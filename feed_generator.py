from xml.etree.ElementTree import Element, SubElement, tostring
import xml.dom.minidom
from datetime import datetime
import os
from utils import create_tables, format_duration, add_channel_metadata, parse_pub_date, get_engine, Episode
from sqlalchemy.orm import sessionmaker

def generate_output_rss_feed(config):
    engine = get_engine(config['database'])
    Session = sessionmaker(bind=engine)
    session = Session()
    create_tables(engine)

    podcast_id = config.get('podcast_id')
    if not podcast_id:
        podcast_id = config.get('output_rss_feed', {}).get('atom_link', {}).get('href', 'default_podcast_id')

    episodes = session.query(Episode).filter(
        Episode.processing_status == 'processed',
        Episode.skipped == False,
        Episode.podcast_id == podcast_id
    ).all()

    session.close()

    episodes.sort(key=lambda episode: parse_pub_date(episode.pub_date), reverse=True)

    if not episodes:
        print("No processed episodes found. Skipping RSS feed generation.")
        return

    rss = Element('rss', version='2.0', attrib={
        'xmlns:content': "http://purl.org/rss/1.0/modules/content/",
        'xmlns:wfw': "http://wellformedweb.org/CommentAPI/",
        'xmlns:dc': "http://purl.org/dc/elements/1.1/",
        'xmlns:atom': "http://www.w3.org/2005/Atom",
        'xmlns:sy': "http://purl.org/rss/1.0/modules/syndication/",
        'xmlns:slash': "http://purl.org/rss/1.0/modules/slash/",
        'xmlns:itunes': "http://www.itunes.com/dtds/podcast-1.0.dtd",
        'xmlns:podcast': "https://podcastindex.org/namespace/1.0",
        'xmlns:rawvoice': "https://blubrry.com/developer/rawvoice-rss/",
        'xmlns:googleplay': "http://www.google.com/schemas/play-podcasts/1.0"
    })

    channel = SubElement(rss, 'channel')
    add_channel_metadata(channel, config['output_rss_feed'])

    SubElement(channel, 'lastBuildDate').text = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')

    for episode in episodes:
        article_guid = episode.article_guid
        title = episode.title
        link = episode.link
        pub_date = episode.pub_date
        description = episode.description
        mp3_file_path = episode.mp3_file_path
        duration = episode.duration
        file_size = episode.file_size

        mp3_url = config['audio_url_prefix']
        if not mp3_url.endswith('/'):
            mp3_url += '/'
        mp3_url += mp3_file_path

        item = SubElement(channel, 'item')
        SubElement(item, 'title').text = title
        SubElement(item, 'link').text = link
        SubElement(item, 'guid', isPermaLink="false").text = article_guid
        SubElement(item, 'pubDate').text = pub_date
        description_text = config['episode_description_template'].format(
            episode_link=link
        )
        SubElement(item, 'description').text = description_text

        enclosure_attribs = {
            'url': mp3_url,
            'type': "audio/mpeg"
        }
        if file_size:
            enclosure_attribs['length'] = str(file_size)
        SubElement(item, 'enclosure', **enclosure_attribs)

        if duration:
            SubElement(item, 'itunes:duration').text = format_duration(duration)

    rough_string = tostring(rss, 'utf-8')
    reparsed = xml.dom.minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="    ")

    with open(config['feed_output_filename'], 'w', encoding='utf-8') as f:
        f.write(pretty_xml)

    print(f"RSS feed generated at {config['feed_output_filename']}")
