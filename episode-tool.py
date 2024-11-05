#!/usr/bin/env python3
import argparse
import sys
import json
from datetime import datetime
from utils import get_engine, create_tables, Episode, slugify
from sqlalchemy.orm import sessionmaker
from content_processing import clean_and_convert_content

def list_episodes(db_url, list_type, exclude_options, podcast_id):
    engine = get_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        query = session.query(Episode).filter(Episode.podcast_id == podcast_id)
        if exclude_options.get('exclude_skipped'):
            query = query.filter(Episode.skipped == False)
        if exclude_options.get('exclude_processed'):
            query = query.filter(Episode.processing_status != 'processed')
        if exclude_options.get('exclude_pending'):
            query = query.filter(Episode.processing_status != 'pending')
        if exclude_options.get('exclude_reprocess'):
            query = query.filter(Episode.processing_status != 'reprocess')

        episodes = query.all()
    finally:
        session.close()

    for episode in episodes:
        print(getattr(episode, list_type))

def select_episode(session, podcast_id, guid=None, title=None, link=None):
    query = session.query(Episode).filter(Episode.podcast_id == podcast_id)
    if guid:
        query = query.filter(Episode.article_guid == guid)
    elif title:
        query = query.filter(Episode.title.like(f"%{title}%"))
    else:
        query = query.filter(Episode.link.like(f"%{link}%"))
    return query.first()

def mark_episode_skipped(db_url, podcast_id, guid=None, title=None, link=None, reprocess=False):
    if not guid and not title and not link:
        print("You must provide either an article GUID, title, or link to identify the episode.")
        sys.exit(1)

    engine = get_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    create_tables(engine)

    try:
        episode = select_episode(session, podcast_id, guid, title, link)
        if not episode:
            print("Episode not found.")
            sys.exit(1)

        if reprocess:
            episode.processing_status = 'reprocess'
            episode.skipped = False
            status = 'reprocess'
        else:
            episode.processing_status = 'skipped'
            episode.skipped = True
            status = 'skipped'
        session.commit()
        print(f"Episode '{episode.title}' status set to '{status}'.")
    finally:
        session.close()

def delete_episode(db_url, podcast_id, guid=None, title=None, link=None):
    if not guid and not title and not link:
        print("You must provide either an article GUID, title, or link to identify the episode.")
        sys.exit(1)

    engine = get_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        episode = select_episode(session, podcast_id, guid, title, link)
        if not episode:
            print("Episode not found.")
            sys.exit(1)
        session.delete(episode)
        session.commit()
        print(f"Episode '{episode.title}' has been deleted from the database.")
    finally:
        session.close()

def add_new_episode(db_url, args, config):
    content = sys.stdin.read()
    if not content.strip():
        print("No content provided. Please provide content via stdin.")
        sys.exit(1)

    podcast_id = config.get('podcast_id')
    if not podcast_id:
        podcast_id = config.get('output_rss_feed', {}).get('atom_link', {}).get('href', 'default_podcast_id')

    engine = get_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    create_tables(engine)

    try:
        # Generate GUID
        if args.guid:
            article_guid = args.guid
        elif args.link:
            article_guid = slugify(args.link)
        else:
            date_str = datetime.utcnow().strftime('%Y%m%d')
            title_slug = slugify(args.title)
            article_guid = f"{date_str}-{title_slug}"

        pub_date = args.date or datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')

        # Determine content format
        if args.html:
            is_markdown = False
        else:
            is_markdown = True  # default is markdown

        content = clean_and_convert_content(content, is_markdown=is_markdown)

        episode = Episode(
            podcast_id=podcast_id,
            article_guid=article_guid,
            title=args.title,
            link=args.link or '',
            pub_date=pub_date,
            description=args.description or '',
            content=content,
            processing_status='pending',
            skipped=False
        )
        session.add(episode)
        session.commit()
        print(f"New episode '{args.title}' added to the database.")
    finally:
        session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage episodes in the database.")
    parser.add_argument("--config", default="config.json", help="Path to configuration file")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--new-episode", action="store_true", help="Add a new episode to the database")
    group.add_argument("--list-guids", action="store_true", help="List all episode GUIDs")
    group.add_argument("--list-links", action="store_true", help="List all episode links")
    group.add_argument("--list-titles", action="store_true", help="List all episode titles")
    group.add_argument("--skip", action="store_true", help="Mark an episode as skipped")
    group.add_argument("--reprocess", action="store_true", help="Set processing_status to 'reprocess'")
    group.add_argument("--delete", action="store_true", help="Delete an episode from the database")

    # Exclude for list
    parser.add_argument("--exclude-skipped", action="store_true", help="Exclude episodes marked for skipping from the list")
    parser.add_argument("--exclude-processed", action="store_true", help="Exclude processed episodes from the list")
    parser.add_argument("--exclude-pending", action="store_true", help="Exclude pending episodes from the list")
    parser.add_argument("--exclude-reprocess", action="store_true", help="Exclude episodes marked for reprocessing from the list")

    parser.add_argument("--guid", help="GUID of the episode to update, add, or delete")
    parser.add_argument("--title", help="Title of the episode to update, add, or delete")
    parser.add_argument("--link", help="Link of the episode to update, add, or delete")
    parser.add_argument("--description", help="Description of the new episode")
    parser.add_argument("--date", help="Publication date of the new episode")
    parser.add_argument("--db", help="Database filename or connection string")

    format_group = parser.add_mutually_exclusive_group()
    format_group.add_argument("--markdown", action="store_true", help="Content is in Markdown format (default)")
    format_group.add_argument("--html", action="store_true", help="Content is in HTML format")

    args = parser.parse_args()

    # Load configuration
    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
            config['config_file_path'] = args.config
    except Exception as e:
        print(f"Error loading configuration file: {e}")
        sys.exit(1)

    # Set default db filename or connection string from config if not provided
    db_url = args.db or config.get('database', 'episodes.db')

    podcast_id = config.get('podcast_id')
    if not podcast_id:
        podcast_id = config.get('output_rss_feed', {}).get('atom_link', {}).get('href', 'default_podcast_id')

    exclude_options = {
        'exclude_skipped': args.exclude_skipped,
        'exclude_processed': args.exclude_processed,
        'exclude_pending': args.exclude_pending,
        'exclude_reprocess': args.exclude_reprocess
    }

    if args.list_guids:
        list_episodes(db_url, 'article_guid', exclude_options, podcast_id)
    elif args.list_links:
        list_episodes(db_url, 'link', exclude_options, podcast_id)
    elif args.list_titles:
        list_episodes(db_url, 'title', exclude_options, podcast_id)
    elif args.new_episode:
        add_new_episode(db_url, args, config)
    elif args.skip or args.reprocess:
        mark_episode_skipped(db_url, podcast_id, guid=args.guid, title=args.title, link=args.link, reprocess=args.reprocess)
    elif args.delete:
        delete_episode(db_url, podcast_id, guid=args.guid, title=args.title, link=args.link)
    else:
        print("Error: No command supplied. Please use one of the available options.")
        parser.print_help()
        sys.exit(1)
