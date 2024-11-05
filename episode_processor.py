from episode_processing_utils import process_episode
from utils import create_tables, parse_pub_date, get_engine, Episode
from sqlalchemy.orm import sessionmaker

def process_pending_episodes(config, reprocess=False, episode_limit=None):
    engine = get_engine(config['database'])
    Session = sessionmaker(bind=engine)
    session = Session()
    create_tables(engine)

    try:
        podcast_id = config.get('podcast_id')
        if not podcast_id:
            podcast_id = config.get('output_rss_feed', {}).get('atom_link', {}).get('href', 'default_podcast_id')

        if reprocess:
            status_clause = Episode.processing_status.in_(['processed', 'pending', 'reprocess'])
        else:
            status_clause = Episode.processing_status.in_(['pending', 'reprocess'])

        episodes_query = session.query(Episode).filter(
            status_clause,
            Episode.skipped == False,
            Episode.podcast_id == podcast_id
        )

        episodes = episodes_query.all()

    finally:
        session.close()

    # Sort episodes by parsed_pub_date, newest first
    episodes.sort(key=lambda episode: parse_pub_date(episode.pub_date), reverse=True)

    if episode_limit:
        episodes = episodes[:episode_limit]

    for episode in episodes:
        process_episode(episode, config)
