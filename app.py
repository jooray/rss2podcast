from flask import Flask, render_template, request, redirect, url_for, flash, g
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from utils import get_engine, create_tables, User as UserModel, Episode
import json
import hashlib
import os
from add_website import add_website_to_db
from web_utils import generate_config, sanitize_username
import secrets
import argparse

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(16))

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

config = {}
engine = None
Session = None

# Initialize database and session maker at the start
def initialize_app(config_path):
    global config, engine, Session
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file '{config_path}' not found. Exiting.")
        exit(1)

    db_url = config.get('database', 'web-episodes.db')
    engine = get_engine(db_url)
    Session = sessionmaker(bind=engine)
    create_tables(engine)

class User(UserMixin):
    def __init__(self, id_, username):
        self.id = id_
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    session = get_db_session()
    user_row = session.query(UserModel).filter(UserModel.id == int(user_id)).first()
    session.close()
    if user_row:
        return User(user_row.id, user_row.username)
    return None

def get_db_session():
    if 'db_session' not in g:
        if Session is None:
            raise RuntimeError("Database session is not initialized. Ensure 'initialize_app()' is called before using the application.")
        g.db_session = Session()
    return g.db_session

@app.teardown_appcontext
def close_db_session(exception):
    db_session = g.pop('db_session', None)
    if db_session is not None:
        db_session.close()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not sanitize_username(username):
            flash('Username can only contain letters, numbers, "-", and "_".')
            return render_template('register.html')
        # Salt and hash the password
        salt = os.urandom(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        # Store salt and hash together
        password_storage = (salt + password_hash).hex()  # Convert to hex string for storage

        session = get_db_session()
        try:
            user = UserModel(username=username, password=password_storage)
            session.add(user)
            session.commit()
            flash('Registration successful. Please log in.')
            return redirect(url_for('login'))
        except IntegrityError:
            session.rollback()
            flash('Username already exists.')
        finally:
            session.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        session = get_db_session()
        user_row = session.query(UserModel).filter(UserModel.username == username).first()
        session.close()
        if user_row:
            stored_password = bytes.fromhex(user_row.password)
            salt = stored_password[:16]
            stored_hash = stored_password[16:]
            password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
            if password_hash == stored_hash:
                user = User(user_row.id, user_row.username)
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.')
        else:
            flash('Invalid username or password.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def dashboard():
    podcast_id = f"{current_user.username}_001"
    feed_config = generate_config(config, podcast_id)
    feed_url = feed_config['output_rss_feed']['atom_link']['href']
    if request.method == 'POST':
        url = request.form['url']
        db_url = config.get('database', 'web-episodes.db')
        add_website_to_db(db_url, url, podcast_id)
        flash("The podcast has been loaded up into the queue, let's roll the tape!")

    return render_template('dashboard.html', feed_url=feed_url)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the Flask application')
    parser.add_argument('--port', type=int, help='Port to run the server on')
    parser.add_argument('--host', help='Host to run the server on')
    parser.add_argument('--config', default='web-config.json', help='Path to the configuration file')

    args = parser.parse_args()

    initialize_app(args.config)

    # Determine host and port
    host = args.host or config.get('listen', {}).get('host', '127.0.0.1')
    port = args.port or config.get('listen', {}).get('port', 5000)

    print(f"Starting server on {host}:{port}")
    app.run(host=host, port=port, debug=False)
