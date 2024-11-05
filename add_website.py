#!/usr/bin/env python3
import argparse
import sys
import json
from datetime import datetime
import trafilatura
from utils import get_engine, create_tables, Episode
from sqlalchemy.orm import sessionmaker

def add_website_to_db(db_url, url, podcast_id):
    # Fetch and extract content using trafilatura
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        print(f"Failed to download content from URL: {url}")
        sys.exit(1)

    content = trafilatura.extract(downloaded, include_comments=False)
    metadata = trafilatura.extract_metadata(downloaded)
    title = metadata.title if metadata and metadata.title else "Untitled"

    if not content.strip():
        print("No content extracted from the URL.")
        sys.exit(1)

    # Generate GUID using the URL
    article_guid = url

    # Get current date and time in the required format
    pub_date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')

    # Connect to the database and insert the episode
    engine = get_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    create_tables(engine)

    episode = Episode(
        podcast_id=podcast_id,
        article_guid=article_guid,
        title=title,
        link=url,
        pub_date=pub_date,
        description='',
        content=content,
        processing_status='pending',
        skipped=False
    )
    session.add(episode)
    session.commit()
    session.close()
    print(f"Website '{title}' added to the database with GUID '{article_guid}' under podcast_id '{podcast_id}'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add a website to the episodes database.")
    parser.add_argument("url", help="URL of the website to add.")
    parser.add_argument("--config", default="config.json", help="Path to configuration file.")
    parser.add_argument("--db", help="Database filename or connection string (overrides config).")

    args = parser.parse_args()

    # Load configuration
    config = {}
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
                config['config_file_path'] = args.config
        except Exception as e:
            print(f"Warning: Could not load configuration file: {e}")
            if not args.db:
                sys.exit(1)

    # Set database filename or connection string
    db_url = args.db or config.get('database', 'episodes.db')

    # Get podcast_id from config
    podcast_id = config.get('podcast_id')
    if not podcast_id:
        podcast_id = config.get('output_rss_feed', {}).get('atom_link', {}).get('href', 'default_podcast_id')

    # Add website to the database
    add_website_to_db(db_url, args.url, podcast_id)
