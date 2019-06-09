import os
import json
import time
APP_NAME = 'CR-unsuck'
APP_VERSION = '0.1'
APP_DATA_DIR = os.path.join('/home/nimesh/.local/share', APP_NAME)
APP_DATA_FILE = os.path.join(APP_DATA_DIR, 'data.json')

if not os.path.exists(APP_DATA_DIR):
    os.makedirs(APP_DATA_DIR)
