import os
import re
import tempfile
import subprocess
from datetime import datetime
from content_processing import prepare_for_speech
from markdown_to_speech import convert_markdown_to_speech
from sqlalchemy.orm import sessionmaker
from utils import slugify, get_engine, Episode
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

def process_episode(episode, config):
    title = episode.title
    content = episode.content

    # Apply preprocess_regexps to content and title if available
    if 'preprocess_regexps' in config:
        content = apply_preprocess_regexps(content, config['preprocess_regexps'])
        title = apply_preprocess_regexps(title, config['preprocess_regexps'])

    print(f"{Fore.GREEN}Processing episode:{Style.RESET_ALL} {title}")

    content = prepare_for_speech(content, config)

    audio_basename = slugify(title)

    # Convert Title to Speech
    title_audio_wav = os.path.join(tempfile.gettempdir(), f"title_audio_{audio_basename}.wav")
    convert_markdown_to_speech(title, title_audio_wav, **config['tts_options'])

    # Convert Markdown to Speech
    content_audio_wav = os.path.join(tempfile.gettempdir(), f"content_audio_{audio_basename}.wav")
    convert_markdown_to_speech(content, content_audio_wav, **config['tts_options'])

    # Apply audio speedup if configured
    if config.get('audio_speedup') and config['audio_speedup'] != 1:
        content_audio_wav = speedup_wav_file(content_audio_wav, config['audio_speedup'])
        title_audio_wav = speedup_wav_file(title_audio_wav, config['audio_speedup'])

    # Combine Audio Files
    final_audio_wav = os.path.join(tempfile.gettempdir(), f"final_audio_{audio_basename}.wav")
    combine_audio_files(
        config.get('prefix_audio_files', []),
        title_audio_wav,
        content_audio_wav,
        config.get('postfix_audio_files', []),
        final_audio_wav
    )

    # Convert to MP3
    mp3_filename = f"{audio_basename}.mp3"
    os.makedirs(config['audio_output_directory'], exist_ok=True)
    mp3_file_path = os.path.join(config['audio_output_directory'], mp3_filename)
    convert_to_mp3(final_audio_wav, mp3_file_path, config['mp3_conversion'])
    duration, file_size = get_mp3_duration_and_size(mp3_file_path)

    # Update Episode Metadata
    episode.processing_status = 'processed'
    episode.processed_date = datetime.utcnow().isoformat()
    episode.mp3_file_path = mp3_filename  # Store the filename instead of full path
    episode.duration = duration
    episode.file_size = file_size
    update_episode_in_db(episode, config['database'])

    # Clean Up Temporary Files
    os.remove(content_audio_wav)
    os.remove(title_audio_wav)
    os.remove(final_audio_wav)

def speedup_wav_file(wav_file, audio_speedup):
    output_wav_file = os.path.join(tempfile.gettempdir(), f"speedup_{os.path.basename(wav_file)}")
    subprocess.run([
        'ffmpeg', '-y', '-i', wav_file, '-filter:a',
        f"atempo={audio_speedup}", output_wav_file
    ], check=True)
    os.remove(wav_file)  # Remove the original file
    return output_wav_file

def combine_audio_files(prefix_files, title_audio_file, content_audio_file, postfix_files, output_file):
    audio_files = []

    # Handle prefix files
    if len(prefix_files) == 0:
        # No prefix files
        pass
    elif len(prefix_files) == 1:
        # One prefix file: prefix + content
        audio_files.extend([prefix_files[0]])
    elif len(prefix_files) == 2:
        # Two prefix files: first prefix + title + second prefix + content
        audio_files.extend([prefix_files[0], title_audio_file, prefix_files[1]])
    else:
        raise ValueError("Prefix files should be either 0, 1, or 2 files.")

    # Add the content audio
    audio_files.append(content_audio_file)

    # Handle postfix files
    if len(postfix_files) == 0:
        # No postfix files
        pass
    elif len(postfix_files) == 1:
        # One postfix file: content + postfix
        audio_files.extend([postfix_files[0]])
    elif len(postfix_files) == 2:
        # Two postfix files: content + first postfix + title + second postfix
        audio_files.extend([postfix_files[0], title_audio_file, postfix_files[1]])
    else:
        raise ValueError("Postfix files should be either 0, 1, or 2 files.")

    # Create a temporary file listing the audio files
    concat_file = tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt')
    for audio_file in audio_files:
        concat_file.write(f"file '{audio_file}'\n")
    concat_file.close()

    # Use ffmpeg to concatenate audio files
    subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i',
        concat_file.name, '-c', 'copy', output_file
    ], check=True)

    os.remove(concat_file.name)

def convert_to_mp3(wav_file, mp3_file, mp3_config):
    os.makedirs(os.path.dirname(mp3_file), exist_ok=True)
    subprocess.run([
        'ffmpeg', '-y', '-i', wav_file, '-codec:a',
        mp3_config.get('codec', 'libmp3lame'),
        '-b:a', mp3_config.get('bitrate', '192k'), mp3_file
    ], check=True)

def get_mp3_duration_and_size(mp3_file_path):
    if not os.path.isfile(mp3_file_path):
        return None, None

    # Get duration using ffprobe
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries',
        'format=duration', '-of',
        'default=noprint_wrappers=1:nokey=1', mp3_file_path
    ]
    try:
        duration = float(subprocess.check_output(cmd).strip())
        file_size = os.path.getsize(mp3_file_path)
        return int(duration), file_size
    except Exception as e:
        print(f"Error processing {mp3_file_path}: {e}")
        return None, None

def update_episode_in_db(episode, db_url):
    """
    Updates the episode's metadata in the database.
    """
    engine = get_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        existing_episode = session.query(Episode).filter(
            Episode.podcast_id == episode.podcast_id,
            Episode.article_guid == episode.article_guid
        ).first()
        if existing_episode:
            existing_episode.processing_status = episode.processing_status
            existing_episode.mp3_file_path = episode.mp3_file_path
            existing_episode.processed_date = episode.processed_date
            existing_episode.duration = episode.duration
            existing_episode.file_size = episode.file_size
            session.commit()
            print(f"Episode '{episode.title}' updated in the database.")
        else:
            print(f"Episode '{episode.title}' not found in the database.")
    except Exception as e:
        session.rollback()
        print(f"Error updating episode in DB: {e}")
    finally:
        session.close()

def apply_preprocess_regexps(text, regexps):
    for item in regexps:
        regexp = item['regexp']
        replacement = item['replacement']
        text = re.sub(regexp, replacement, text)
    return text
