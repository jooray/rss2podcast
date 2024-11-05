import json
import re

def generate_config(config_template, podcast_id):
    config_str = json.dumps(config_template)
    config_str = config_str.replace('{podcast_id}', podcast_id)
    config = json.loads(config_str)
    config['podcast_id'] = podcast_id
    return config

def sanitize_username(username):
    if re.match(r'^[a-zA-Z0-9_-]+$', username):
        return True
    else:
        return False
