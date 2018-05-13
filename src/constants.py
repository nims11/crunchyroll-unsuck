import os
import json
import time
APP_NAME = 'CR-unsuck'
APP_VERSION = '0.1'
APP_DATA_DIR = os.path.join('/home/nimesh/.local/share', APP_NAME)
APP_DATA_FILE = os.path.join(APP_DATA_DIR, 'data.json')

if not os.path.exists(APP_DATA_DIR):
    os.makedirs(APP_DATA_DIR)

CONFIG = {}
try:
    with open(APP_DATA_FILE) as f:
        CONFIG = json.loads(f.read())
except IOError:
    pass

def save_config():
    with open(APP_DATA_FILE, 'w') as f:
        f.write(json.dumps(CONFIG))


def update_history(episode, playhead, total=None):
    global CONFIG
    if 'playhead' not in CONFIG:
        CONFIG['playhead'] = {}
    CONFIG['playhead'][episode] = {
        'playhead': playhead,
        'total': total,
        'completed': False,
        'timestamp': int(time.time())
    }
    if total and total - playhead < 180:
        CONFIG['playhead'][episode]['completed'] = True
    save_config()


def get_history(episode):
    return CONFIG.get('playhead', {}).get(episode, {})


def get_last_accessed(episode):
    return get_history(episode).get('timestamp', 0)


def get_playhead(episode):
    return get_history(episode).get('playhead', 0)


def get_total_time(episode):
    return get_history(episode).get('total', -1)


def get_completed_status(episode):
    return get_history(episode).get('completed', False)
