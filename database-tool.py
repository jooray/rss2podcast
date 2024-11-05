#!/usr/bin/env python3
import argparse
from utils import get_engine, create_tables, Episode, User
from sqlalchemy.orm import sessionmaker

def create_db(db_url):
    engine = get_engine(db_url)
    create_tables(engine)
    print(f"Database tables created in {db_url}")

def migrate_db(from_db_url, to_db_url):
    from_engine = get_engine(from_db_url)
    to_engine = get_engine(to_db_url)

    from_Session = sessionmaker(bind=from_engine)
    to_Session = sessionmaker(bind=to_engine)

    create_tables(to_engine)

    from_session = from_Session()
    to_session = to_Session()

    try:
        # Migrate Episodes
        episodes = from_session.query(Episode).all()
        for episode in episodes:
            to_session.merge(episode)
        # Migrate Users
        users = from_session.query(User).all()
        for user in users:
            to_session.merge(user)
        to_session.commit()
        print(f"Migration from {from_db_url} to {to_db_url} completed successfully.")
    except Exception as e:
        to_session.rollback()
        print(f"Error during migration: {e}")
    finally:
        from_session.close()
        to_session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Database management tool.")
    subparsers = parser.add_subparsers(dest='command')

    # Create command
    create_parser = subparsers.add_parser('create', help='Create database tables.')
    create_parser.add_argument('--db', required=True, help='Database filename or connection string.')

    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Migrate database.')
    migrate_parser.add_argument('--from', dest='from_db', required=True, help='Source database filename or connection string.')
    migrate_parser.add_argument('--to', dest='to_db', required=True, help='Destination database filename or connection string.')

    args = parser.parse_args()

    if args.command == 'create':
        create_db(args.db)
    elif args.command == 'migrate':
        migrate_db(args.from_db, args.to_db)
    else:
        parser.print_help()
