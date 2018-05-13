import os
import json
APP_NAME = 'CR-unsuck'
APP_VERSION = '0.1'
APP_DATA_DIR = '~/.local/.share/'
APP_DATA_FILE = os.path.join(APP_DATA_DIR, APP_NAME)

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
