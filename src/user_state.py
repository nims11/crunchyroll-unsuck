""" Utilities to maintain and query user state """
import json
import os
import logging
import time
import atexit
from dataclasses import dataclass
from collections import defaultdict
from typing import Optional


class UserState:
    """ User state class """

    CONFIG_TEMPLATE = {"item_history": {}, "playhead": {}}

    def __init__(self, state_file_path: str):
        self.state_file_path = state_file_path
        atexit.register(self.save_state)
        try:
            if not os.path.exists(state_file_path):
                logging.info("State file (%s) doesn't exist, creating one", state_file_path)
                with open(state_file_path, "w") as state_file:
                    json.dump(UserState.CONFIG_TEMPLATE, state_file_path)
            with open(state_file_path) as state_file:
                self._config = json.load(state_file)
        except Exception as exp:
            self.state_file_path = None
            logging.error("State file error (%s), using dummy state file", str(exp))
            self._config = UserState.CONFIG_TEMPLATE

    def save_state(self):
        """ Save state to file """
        if self.state_file_path:
            try:
                with open(self.state_file_path, 'w') as state_file:
                    json.dump(self._config, state_file)
            except Exception as exp:
                logging.error("Couldn't save state file: %s", str(exp))

    def record_history(self, episode: str, playhead: int, total: Optional[int] = None) -> None:
        """ Record history for an episode """
        self._config['playhead'][episode] = {
            'playhead': playhead,
            'timestamp': int(time.time()),
            'completed': (total and total - playhead < 180)
        }

    def get_playhead(self, episode: str) -> int:
        return self._config['playhead'].get(episode, {}).get('playhead', 0)

    def get_completed_status(self, episode: str) -> bool:
        return self._config['playhead'].get(episode, {}).get('completed', False)

    def get_last_accessed(self, episode: str) -> int:
        return self._config['playhead'].get(episode, {}).get('timestamp', 0)
