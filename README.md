# RSS-to-Podcast Converter

A Python-based application that converts blog posts from an RSS feed into a value-for-value-enabled podcast, allowing listeners to engage with content via audio. This project automates the transformation of blog articles into podcast episodes by using text-to-speech technology, providing an easy way for listeners to consume written content as audio.

Another use-case is converting websites into podcast episodes. They are added manually using `add_website.py`. In this case, there is no source RSS feed.

For this use-case, there is also a web application, where users can generate their own podcast feed from articles they want to read. It powers [loaditfor.me](https://loaditfor.me/). Feel free to run your own instance, see [README-web.md](README-web.md).

## Overview

The RSS-to-Podcast Converter pulls articles from an RSS feed, processes the content using a text-to-speech (TTS) model, and generates podcast episodes in MP3 format. The episodes are then assembled into an RSS feed compatible with podcast players, complete with metadata, audio, and descriptions. The generated podcast includes a **value-for-value** system, enabling micropayments and splits for creators via the Lightning Network.

This project uses a database to track processed episodes and ensure each article is only converted once. It allows manual skipping of articles that may not be suitable for TTS conversion, such as posts with embedded videos or images.

## Features

- **Automated Podcast Generation**: Converts blog articles from an RSS feed into podcast episodes using a TTS model.
- **Customizable Episode Templates**: Configurable episode description templates to link back to the original article.
- **Configurable Audio Stitching**: Customizable introduction and conclusion audio segments for each episode.
- **Value-for-Value Integration**: Supports micropayments with customizable splits, allowing listeners to contribute directly.
- **Automatic Skipping and Reprocessing**: Tracks processed articles to avoid duplicate conversions, with options to reprocess episodes if necessary.
- **Optional LLM Processing and Verification**: Uses an LLM to optimize text for TTS and verifies the content to avoid unsuitable output.
- **Customizable Output**: Allows custom intro, outro, and conversion settings for generated MP3 files.
- **Manual Episode Addition**: Supports adding episodes manually without a source RSS feed.
- **Flexible Feed Generation**: Can regenerate the RSS feed without processing episodes.
- **Website Content Addition**: Adds content from any website URL directly into the database for processing.
- **Support for SQLite and PostgreSQL**: Now supports both SQLite and PostgreSQL databases via SQLAlchemy.

## Skipping Podcast Entries

A new configuration option lets you automatically skip episodes whose titles match one or more regular expressions. This is especially useful if, for example, you want to avoid reprocessing content that is already in audio form. To use this feature, add a `skip_regexps` array to your configuration file. For instance, to skip any episode whose title contains "audio" or "Audio", add the following:

```json
"skip_regexps": [
  "[Aa]udio"
]
```

When processing the RSS feed, if an episode’s title matches any of these patterns, the episode is immediately marked as skipped and is not converted to speech.

## Dependencies

Install dependencies using Poetry:

```bash
poetry install
poetry add psycopg2-binary # for postgresql support
```

## Database Options

This application supports both SQLite and PostgreSQL databases via SQLAlchemy.

### Configuring the Database

In your configuration file (`config.json`), you can specify the database connection using the `database_url` parameter.

- **SQLite (Default)**: If you provide a filename in `database`, the application will use SQLite.
- **PostgreSQL**: If you provide a PostgreSQL connection string (starting `postgresql://`) in `database_url` or `database`, the application will connect to the specified PostgreSQL database.

Example of using PostgreSQL in `config.json`:

```json
{
  "database_url": "postgresql://user:password@localhost:5432/mydatabase",
  ...
}
```

### Creating Database Tables

You need to create the database tables before running the application. Use the `database-tool.py` script to create tables.

For SQLite:

```bash
python database-tool.py create --db episodes.db
```

For PostgreSQL:

```bash
python database-tool.py create --db postgresql://user:password@localhost:5432/mydatabase
```

### Migrating Between Databases

To migrate data between SQLite and PostgreSQL, use the `migrate` command in `database-tool.py`.

Example migrating from SQLite to PostgreSQL:

```bash
python database-tool.py migrate --from episodes.db --to postgresql://user:password@localhost:5432/mydatabase
```

Example migrating from PostgreSQL to SQLite:

```bash
python database-tool.py migrate --from postgresql://user:password@localhost:5432/mydatabase --to episodes.db
```

## Configuration

The project uses a JSON configuration file to define input sources, output settings, and TTS processing details. See the sample configuration file (`config.json.sample`) for details.

## Running the Application

When running the application, it will use the database specified in your configuration file.

For example:

```bash
python main.py --config config.json
```

## Managing the Database

Use the `database-tool.py` script to manage your database, including creating tables and migrating data.

### Creating Tables

```bash
python database-tool.py create --db [database_url_or_filename]
```

### Migrating Data

```bash
python database-tool.py migrate --from [source_db_url_or_filename] --to [destination_db_url_or_filename]
```

## Usage

### Running the Conversion

The project includes a command-line interface to manage feed processing. Use the following command to start processing the feed:

```bash
python main.py --config config.json
```

### Command-Line Options for `main.py`

- `--config`: Path to the configuration JSON file.
- `--episode-limit`: Limit the number of episodes to process.
- `--episode-guid`: Process a specific episode by GUID.
- `--reprocess`: Reprocess episodes that are already marked as processed.
- `--only-feed`: Generate the RSS feed without processing episodes.

Example:

```bash
python main.py --config config.json --episode-limit 10 --reprocess
```

### Managing Episodes with `episode-tool.py`

`episode-tool.py` allows you to manage episodes in the database, including adding new episodes manually.

#### Adding a New Episode Manually

```bash
echo "This is the content of the episode." | python episode-tool.py --new-episode --title "Episode Title" --config config.json
```

- **Options**:
  - `--new-episode`: Add a new episode to the database.
  - `--title`: Title of the episode (required).
  - `--guid`: GUID for the episode (optional). If not provided, it's generated based on the link or the current date and title.
  - `--link`: Link associated with the episode (optional).
  - `--description`: Description of the episode (optional).
  - `--date`: Publication date of the episode (optional). Defaults to the current date and time.
  - `--markdown`: Content is in Markdown format (default).
  - `--html`: Content is in HTML format.
  - `--config`: Path to the configuration JSON file.

#### Other Episode Management Commands

- **List All Episode GUIDs**:

  ```bash
  python episode-tool.py --list-guids --config config.json
  ```

- **Mark an Episode as Skipped**:

  ```bash
  python episode-tool.py --guid "episode-guid" --skip --config config.json
  ```

- **Reprocess an Episode**:

  ```bash
  python episode-tool.py --guid "episode-guid" --reprocess --config config.json
  ```

- **Delete an Episode**:

  ```bash
  python episode-tool.py --guid "episode-guid" --delete --config config.json
  ```

### Adding a Website with `add_website.py`

`add_website.py` allows you to add content from any website URL directly into the database for processing.

#### Usage

```bash
python add_website.py "https://example.com/article" --config config.json
```

- **Positional Arguments**:
  - `url`: The URL of the website to add.

- **Options**:
  - `--config`: Path to the configuration JSON file (optional, defaults to `config.json`).
  - `--db`: Database filename or connection string (overrides the one specified in the config file).

#### Example

```bash
python add_website.py "https://example.com/blog-post" --db episodes.db
```

This command fetches the content and title from the provided URL using the `trafilatura` library and adds it to the database with the status set to `pending`. The content will then be processed the next time you run `main.py`.

## Preprocessing with Regular Expressions

You can specify optional preprocessing regular expressions in your configuration file under the `preprocess_regexps` key. This feature allows you to define an array of regular expressions and their replacements, which will be applied to both the title and content before converting them to speech.

### Example Configuration

```json
"preprocess_regexps": [
  {
    "regexp": " 1-2 ",
    "replacement": " one to two "
  },
  {
    "regexp": "\\bAI\\b",
    "replacement": "Artificial Intelligence"
  }
]
```

## Is this free?

This project is free to use, modify, etc. It is a free and open source software.

I invested quite a lot of work into this project and related projects that made speech to text possible. I ask you to leave the generated value4value block intact (you can add your splits via config).

[If you found this useful, I appreciate returning the value - pay what it's worth to you](https://juraj.bednar.io/en/support-me/).
