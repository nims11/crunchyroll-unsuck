import os
import json
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
    CONFIG['playhead'][episode] = {'playhead': playhead, 'total': total}
    save_config()
