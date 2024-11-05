# Web Interface for RSS-to-Podcast Converter

This document explains how to set up and use the web interface for the RSS-to-Podcast Converter. The web interface allows users to create accounts, add websites to their personal podcast feed, and obtain their personalized RSS feed URL.

## Overview

The web application provides:

- **User Registration and Login**: Users can create accounts and log in securely.
- **Personalized Podcast Feed**: Each user gets a unique podcast feed identified by their username.
- **Adding Websites**: Users can add any website URL to their feed, which will be processed and converted into podcast episodes.
- **Lo-fi 8-bit ZX Spectrum Style**: The user interface is designed with a retro aesthetic.

## Setup Instructions

### Prerequisites

- Python 3.x
- Required Python packages (install via `pip` or `poetry`):
  - Flask
  - Flask-Login
  - SQLAlchemy
  - Other dependencies from the main project

### Database Recommendation

**Important**: For the web application, it is highly recommended to use PostgreSQL instead of SQLite due to potential locking issues with multiple users accessing the database simultaneously.

### Environment Variables

#### `FLASK_SECRET_KEY`

The application uses a secret key for session management. You can set the secret key via the `FLASK_SECRET_KEY` environment variable. If this variable is not set, the application will generate a random secret key every time it starts. This approach is suitable for development but not recommended for production.

### Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/yourusername/rss-to-podcast.git
   cd rss-to-podcast
   ```

2. **Install Dependencies**

   To install with web interface support, include the `web` dependency group:

   ```bash
   poetry install --with web
   ```

   This installs additional dependencies required for the web interface, including `Flask`, `Flask-Login`, and `SQLAlchemy`.

3. **Prepare the Database**

   - Create a PostgreSQL database for the application.
   - Use the `database-tool.py` script to create the necessary tables:

     ```bash
     python database-tool.py create --db postgresql://user:password@localhost:5432/mydatabase
     ```

4. **Configure the Web Application**

   - Update `web-config.json` to include your PostgreSQL connection string:

     ```json
     {
       "database": "postgresql://user:password@localhost:5432/mydatabase",
       ...
     }
     ```

   - Ensure the `web-config.json` template is in the project root directory.
   - Set the `FLASK_SECRET_KEY` environment variable for security.

### Running the Web Application

Start the Flask web server:

```bash
python app.py --config web-config.json
```

The application will be accessible at `http://localhost:5000`.

### Running the Queue Processor

In a separate terminal, run the process that handles the queue of pending episodes:

```bash
python process_website_queue.py --config web-config.json
```

This script continuously checks for pending episodes and processes them.

## Usage Instructions

### Registering an Account

1. Navigate to `http://localhost:5000/register`.
2. Fill in a username and password.
3. Submit the form to create your account.

### Logging In

1. Go to `http://localhost:5000/login`.
2. Enter your username and password.
3. Click "Login" to access your dashboard.

### Dashboard

After logging in, you will see:

- **Your Personalized RSS Feed URL**: This is the URL you can add to your podcast player to receive your episodes.
- **Copy Icon**: Click this icon to copy the feed URL to your clipboard.
- **Add Website**: An input box where you can enter a website URL.
- **"Load it up" Button**: Click this to add the website to your processing queue.

### Adding a Website

1. Enter the full URL of the website you want to convert into a podcast episode.
2. Click "Load it up".
3. You will receive a confirmation message: "The podcast has been loaded up into the queue, let's roll the tape!"

### Accessing Your Podcast Feed

- Copy your personalized RSS feed URL from the dashboard.
- Add this URL to your preferred podcast app to receive your episodes once they're processed.

## Customization

### Retro Styling

The user interface is styled to resemble 8-bit ZX Spectrum graphics. You can customize the templates and CSS in the `templates` and `static` directories to modify the appearance.

### Config Template

The `web-config.json` file serves as the base configuration for all users. Placeholders like `{podcast_id}` are replaced with the user's specific details at runtime.

### Security Considerations

- Replace `app.secret_key` in `app.py` with a secure, random value.
- Ensure that the database is secured and not accessible from the web.
- Use PostgreSQL for better concurrency and to avoid locking issues.

## Troubleshooting

- **Database Errors**: Ensure the database credentials are correct and the database is running.
- **Processing Issues**: Check the logs of `process_website_queue.py` for any errors during episode processing.

## Additional Information

- The web interface interacts with the existing processing scripts, reusing the core functionality.
- Users are isolated by their `podcast_id`, which is derived from their username.
