import feedparser
import re
from utils import create_tables, slugify, get_engine, Episode
from datetime import datetime
from content_processing import clean_and_convert_content
from sqlalchemy.orm import sessionmaker

def download_and_insert_articles(config, episode_limit=None, specific_episode_guid=None, reprocess=False):
    feed_url = config.get('source_rss_feed_url')
    if not feed_url:
        print("No source RSS feed URL provided. Skipping feed download.")
        return

    process_articles_since = config.get('process_articles_since')
    if process_articles_since:
        try:
            process_date = parse_config_date(process_articles_since)
        except ValueError as e:
            print(f"Error parsing process_articles_since date: {e}. Allowed formats: YYYY, MM-YYYY, DD-MM-YYYY or RSS pubDate format")
            return

    podcast_id = config.get('podcast_id')
    if not podcast_id:
        podcast_id = config.get('output_rss_feed', {}).get('atom_link', {}).get('href', 'default_podcast_id')

    feed = feedparser.parse(feed_url)
    engine = get_engine(config['database'])
    Session = sessionmaker(bind=engine)
    session = Session()
    create_tables(engine)

    try:
        episodes_added = 0

        for entry in feed.entries:
            article_guid = entry.get('id') or entry.get('guid') or entry.link

            if specific_episode_guid and article_guid != specific_episode_guid:
                continue

            pub_date = entry.get('published', datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000'))
            try:
                entry_date = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %z')
            except ValueError:
                # Try ISO 8601 format
                entry_date = datetime.strptime(pub_date, '%Y-%m-%dT%H:%M:%S%z')
            if process_articles_since:
                if entry_date.date() < process_date.date():
                    continue

            existing_episode = session.query(Episode).filter(
                Episode.podcast_id == podcast_id,
                Episode.article_guid == article_guid
            ).first()

            # If an episode already exists and is marked as skipped, simply continue.
            if existing_episode and existing_episode.skipped:
                continue

            # Check if the episode should be skipped based on title matching any skip_regexps
            skip_regexps = config.get('skip_regexps', [])
            if skip_regexps and any(re.search(pattern, entry.title) for pattern in skip_regexps):
                print(f"Skipping article '{entry.title}' because it matches a skip pattern.")
                continue

            content = entry.get('content', [{'value': ''}])[0]['value']
            if not content:
                content = entry.get('description') or ''
            is_markdown = False  # Assume content from feed is HTML
            content = clean_and_convert_content(content, is_markdown)

            if existing_episode:
                if existing_episode.processing_status == 'reprocess' or reprocess:
                    # Update episode with new metadata and mark as pending
                    print(f"Will reprocess article '{entry.title}'.")
                    existing_episode.title = entry.title
                    existing_episode.link = entry.link
                    existing_episode.pub_date = pub_date
                    existing_episode.description = entry.get('summary', '')
                    existing_episode.content = content
                    existing_episode.processing_status = 'pending'
                    session.commit()
                    print(f"Episode '{existing_episode.title}' updated and marked for reprocessing.")
                else:
                    continue  # Episode already exists and is not marked for reprocessing
            else:
                episode = Episode(
                    podcast_id=podcast_id,
                    article_guid=article_guid,
                    title=entry.title,
                    link=entry.link,
                    pub_date=pub_date,
                    description=entry.get('summary', ''),
                    content=content,
                    processing_status='pending',
                    skipped=False
                )
                session.add(episode)
                session.commit()
                episodes_added += 1
                print(f"Episode '{episode.title}' added to the database.")

                if episode_limit and episodes_added >= episode_limit:
                    break
    finally:
        session.close()

def parse_config_date(date_string):
    formats = [
        '%Y',          # YYYY
        '%m-%Y',       # MM-YYYY
        '%d-%m-%Y',    # DD-MM-YYYY
        '%a, %d %b %Y %H:%M:%S %z',  # RSS pubDate format
        '%Y-%m-%dT%H:%M:%S%z' # ISO8601 format
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unable to parse date: {date_string}")
