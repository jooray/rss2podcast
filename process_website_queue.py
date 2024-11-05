#!/usr/bin/env python3
import time
import json
import argparse
import subprocess
from episode_processor import process_episode
from utils import create_tables, get_engine, Episode
from feed_generator import generate_output_rss_feed
from web_utils import generate_config
from sqlalchemy.orm import sessionmaker

def process_website_queue(config_template_file, after_command=None):
    # Load config template once at the start
    with open(config_template_file, 'r') as f:
        config_template = json.load(f)

    while True:
        db_url = config_template.get('database','web-episodes.db')
        engine = get_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        create_tables(engine)

        try:
            pending_episodes = session.query(Episode).filter(
                Episode.processing_status == 'pending'
            ).all()
        finally:
            session.close()

        if pending_episodes:
            print(f"Found {len(pending_episodes)} episode(s) to process.")
            for episode in pending_episodes:
                podcast_id = episode.podcast_id
                config = generate_config(config_template, podcast_id)
                process_episode(episode, config)
                # After processing each episode, regenerate the feed
                generate_output_rss_feed(config)
                # If after_command is specified, execute it
                if after_command:
                    subprocess.run(after_command, shell=True)
        else:
            print("No episodes to process. Sleeping for 60 seconds.")
            time.sleep(60)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process website queue")
    parser.add_argument('--config', default='web-config.json', help='Path to configuration template file')
    parser.add_argument('--after-command', help='Command to execute after each feed is generated')
    args = parser.parse_args()
    process_website_queue(args.config, args.after_command)
