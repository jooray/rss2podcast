#!/usr/bin/env python3
import argparse
import json
import sys
from feed_downloader import download_and_insert_articles
from episode_processor import process_pending_episodes
from feed_generator import generate_output_rss_feed

def main():
    parser = argparse.ArgumentParser(description="Convert blog RSS feed to podcast")
    parser.add_argument('--config', default='config.json', help='Path to configuration file')
    parser.add_argument('--episode-limit', type=int, help='Limit the number of episodes to process')
    parser.add_argument('--episode-guid', help='GUID of a specific episode to process')
    parser.add_argument('--reprocess', action='store_true', help='Reprocess episodes even if already processed')
    parser.add_argument('--only-feed', action='store_true', help='Only generate the RSS feed without processing episodes')

    args = parser.parse_args()

    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
            config['config_file_path'] = args.config
    except Exception as e:
        print(f"Error loading configuration file: {e}")
        sys.exit(1)

    if 'podcast_id' not in config:
        config['podcast_id'] = config.get('output_rss_feed', {}).get('atom_link', {}).get('href', 'default_podcast_id')

    if not args.only_feed:
        if config.get('source_rss_feed_url'):
            download_and_insert_articles(config, episode_limit=args.episode_limit, specific_episode_guid=args.episode_guid, reprocess=args.reprocess)
        process_pending_episodes(config, reprocess=args.reprocess, episode_limit=args.episode_limit)

    generate_output_rss_feed(config)

if __name__ == '__main__':
    main()
