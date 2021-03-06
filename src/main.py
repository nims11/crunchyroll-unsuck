""" Main app script
"""
import sys
import subprocess
import curses
import logging
from typing import List, Union, Optional

import constants
import api.crunchyroll as crapi
from config import USER, PASS
from gui import ItemWidget, BrowserWidget, ContainerWidget, LogWidget, InactiveItemWidget
from gui import ShortcutWidget
from gui import BaseLayout, HorizontalLayout, VerticalLayout, Value, App, ValueType
from user_state import UserState

api = crapi.CrunchyrollAPI(username=USER, password=PASS)
user_state = UserState(constants.APP_DATA_FILE)


class GUIHandler(logging.StreamHandler):

    def __init__(self, handler):
        logging.StreamHandler.__init__(self)
        self.handler = handler

    def emit(self, record):
        self.handler(self.format(record))


class Episode:
    """ Base episode class
    """

    def get_id(self) -> str:
        """ ID used in cache files
        """

    def open(self) -> None:
        """ Opens the episode and sets the playhead
        """

    def get_number(self) -> str:
        """ Get episode number
        """

    def get_name(self) -> str:
        """ Get episode name
        """

    def get_collection(self) -> str:
        """ Get collection (season/sub/dub) the episode belongs to
        """


class CREpisode(Episode):
    """ Crunchyroll Episode class
    """

    def __init__(self, data: dict, anime_id: str = None):
        self.data = data
        self.anime_id = anime_id

    def get_id(self):
        return "CR-" + self.data["media_id"]

    def open(self):
        user_state.update_item_access(self.anime_id)
        playhead = max(0, user_state.get_playhead(self.get_id()) - 5)
        mpv_args = " ".join([
            f"--start={playhead}",
            "--term-status-msg \"Playback Status: ${{=time-pos}} ${{=duration}}\"",
            "--cache=yes --cache-secs=300 --force-seekable=yes --hr-seek=yes",
            "--hr-seek-framedrop=yes",
            "{filename}"
        ])
        # mpv_args = (
        #     "--start=%d " % playhead
        # ) + '--term-status-msg "Playback Status: ${{=time-pos}} ${{=duration}} " {filename}'
        args = [
            "streamlink",
            self.data["url"],
            "best",
            "--verbose-player",
            "--player", "mpv",
            "--player-args",
            mpv_args
        ]
        player_process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        logging.info("$ " + " ".join(args))
        playhead = None
        for line in player_process.stdout:
            try:
                line = line.strip()
                if "Playback Status:" in line:
                    playhead, total_time = [float(x) for x in line.split()[-2:]]
                    user_state.record_history(self.get_id(), playhead)
            except Exception as exp:
                logging.warning("Error parsing player stdout (%s): %s", line, str(exp))

        if playhead:
            user_state.record_history(self.get_id(), playhead, total_time)
        else:
            user_state.record_history(self.get_id(), 0)
        player_process.wait()

    def get_number(self):
        return self.data["episode_number"]

    def get_name(self):
        return self.data["name"]

    def get_collection(self):
        return self.data.get("collection_id", None)


class Anime:
    """ Base Anime class
    """

    def get_id(self) -> str:
        """ Get anime id
        """

    def get_collections(self) -> List[str]:
        """ Get a list of collections
        """

    def get_episodes(self) -> List[Episode]:
        """ Get list of episodes
        """

    def get_name(self) -> str:
        """ Get name of anime
        """


class CRAnime(Anime):
    """ Crunchyroll Anime
    """

    def __init__(self, data):
        self.data = data

    def get_id(self):
        return "CR-" + self.data["series_id"]

    def get_episodes(self):
        logging.info("Fetching episodes...")
        episodes = [
            CREpisode(episode, anime_id=self.get_id())
            for episode in api.list_media(series_id=self.data["series_id"], sort=crapi.SortOption.DESC, limit=1000)
        ]
        logging.info("Fetched %d episodes" % len(episodes))
        return episodes

    def get_collections(self):
        logging.info("Fetching collections...")
        collections = api.list_collections(series_id=self.data["series_id"], limit=50)
        collections = {c["collection_id"]: c["name"] for c in collections}
        logging.info("Fetched %d collections" % len(collections))
        return collections

    def get_name(self):
        return self.data["name"]


class Directory:
    """ Directory base class
    """

    def __init__(self, name: str, parent: Optional["Directory"] = None):
        self.name = name
        self.parent = parent
        self.children = []  # type: List[Union[Directory, Anime]]
        if self.parent:
            self.parent.add_child(self)

    def get_name(self) -> str:
        """ Get directory name
        """
        return self.name

    def get_content(self) -> List[Union["Directory", Anime]]:
        """ Get content of directory
        """
        return self.children

    def get_parent(self) -> Optional["Directory"]:
        """ Get directory parent
        """
        return self.parent

    def add_child(self, child: Union["Directory", Anime]) -> None:
        """ Add content to directory
        """
        if isinstance(child, Directory):
            child.parent = self
        self.children.append(child)

    def delete_entry(self, item) -> bool:
        """ Delete entry
        """

    def get_shortcuts(self) -> List:
        """ Get shortcuts for bottom bar
        """
        return [("q", "exit", lambda _: sys.exit())]


class CRQueueDirectory(Directory):
    """ Directory showing the Crunchyroll queue
    """

    def get_content(self):
        return [self.parent] + sorted(
            [CRAnime(anime["series"]) for anime in api.get_queue("anime")],
            key=lambda x: (-user_state.get_item_last_accessed(x.get_id()), x.get_name()),
        )

    def delete_entry(self, item: CRAnime):
        return api.remove_from_queue(item.data["series_id"])

    def get_shortcuts(self):
        return [
            (
                "s",
                "sort",
                [
                    ("n", "sort by name", self.sort),
                    ("r", "sort by recently watched", self.sort),
                    ("n", "sort by name", self.sort),
                ],
            ),
            ("d", "delete", self.delete_entry),
        ] + super().get_shortcuts()

    def sort(self):
        pass


def generate_control_switch(lst, active=0):
    cur_control_idx = active
    lst_dict = {}
    for idx, (key, obj) in enumerate(lst):
        obj.unfocus()
        lst_dict[key] = idx
        lst[idx] = obj
    lst[active].focus()

    def _next_switch():
        nonlocal cur_control_idx
        lst[cur_control_idx].unfocus()
        lst[cur_control_idx].redraw()
        cur_control_idx = (cur_control_idx + 1) % len(lst)
        lst[cur_control_idx].focus()
        lst[cur_control_idx].redraw()
        lst[cur_control_idx].get_app().set_control(lst[cur_control_idx])

    def _prev_switch():
        nonlocal cur_control_idx
        lst[cur_control_idx].unfocus()
        lst[cur_control_idx].redraw()
        cur_control_idx = (cur_control_idx - 1 + len(lst)) % len(lst)
        lst[cur_control_idx].focus()
        lst[cur_control_idx].redraw()
        lst[cur_control_idx].get_app().set_control(lst[cur_control_idx])

    def _switch_to(key):
        nonlocal cur_control_idx
        lst[cur_control_idx].unfocus()
        lst[cur_control_idx].redraw()
        cur_control_idx = lst_dict[key]
        lst[cur_control_idx].focus()
        lst[cur_control_idx].redraw()
        lst[cur_control_idx].get_app().set_control(lst[cur_control_idx])

    return _prev_switch, _next_switch, _switch_to


class MyApp(App):
    def __init__(self, stdscr):
        super().__init__(stdscr, BaseLayout(Value(curses.COLS), Value(curses.LINES), None))
        self._setup_logging()
        self._setup_layout()

    def _setup_logging(self):
        """ Setup logging handler """
        ch = GUIHandler(self.log)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logging.getLogger().handlers = []
        logging.basicConfig(
            level=logging.INFO,
            datefmt='%I:%M:%S',
            handlers=[ch]
        )

    def _setup_layout(self):
        """ Setup layout """
        main_container = ContainerWidget(
            self.root,
            False,
            constants.APP_NAME + " v" + constants.APP_VERSION,
            center=True,
            style=(curses.A_BOLD | curses.A_UNDERLINE),
        )
        l4 = VerticalLayout(Value(1, ValueType.VAL_RELATIVE), Value(1, ValueType.VAL_RELATIVE), main_container)

        l1 = HorizontalLayout(Value(1, ValueType.VAL_RELATIVE), Value(0.8, ValueType.VAL_RELATIVE), l4)
        l2 = BaseLayout(Value(0.3, ValueType.VAL_RELATIVE), Value(1, ValueType.VAL_RELATIVE), l1)

        l5 = BaseLayout(Value(1, ValueType.VAL_RELATIVE), Value(-1, ValueType.VAL_ABSOLUTE), l4)
        c3 = ContainerWidget(l5, True, "Log")
        self.set_log_widget(LogWidget(c3))

        c1 = ContainerWidget(l2, True, "Anime")
        c2 = ContainerWidget(l1, True, "Episodes")
        lst1 = BrowserWidget(c1)
        lst2 = BrowserWidget(c2)
        self.anime_list_widget = lst1
        self.episode_list_widget = lst2
        self.directory_container = c1
        self.episode_container = c2

        self.anime_view_shortcuts = [
            ("s", "sort", sys.exit),
            ("d", "delete", self.delete_entry),
            ("q", "exit", lambda _: sys.exit()),
        ]
        s1 = ShortcutWidget(l4, lst1, self.anime_view_shortcuts)

        self.init_directories()
        # Register events
        self.root.register_event("q", lambda _: sys.exit())
        self.prev_switch, self.next_switch, self.switch_to = generate_control_switch(
            [("anime", lst1), ("episodes", lst2)], active=0
        )
        l1.register_event("l", lambda _: self.next_switch())
        l1.register_event("KEY_RIGHT", lambda _: self.next_switch())
        l1.register_event("h", lambda _: self.prev_switch())
        l1.register_event("KEY_LEFT", lambda _: self.prev_switch())
        lst1.register_event("\n", self.list_content)
        lst2.register_event("\n", self.open_episode)
        self.set_control(lst1)

    def init_directories(self):
        self.root_directory = Directory("")
        CRQueueDirectory("CR Queue", self.root_directory)
        self.anime_list_widget.set_data(self.root_directory)
        for content in self.root_directory.get_content():
            ItemWidget(self.anime_list_widget, content.get_name(), content)

    def tablize(self, rows, extra_padding):
        ret = []
        offset = []
        prev_offset = 0
        for col in range(len(rows[0])):
            offset.append(0)
            for row in rows:
                ret.append("")
                offset[-1] = max(offset[-1], prev_offset + len(row[col]) + extra_padding)
            prev_offset = offset[-1]

        for col in range(len(rows[0])):
            for idx, row in enumerate(rows):
                ret[idx] += row[col]
                if col != len(rows[0]) - 1:
                    ret[idx] += " " * (offset[col] - len(ret[idx]))

        return ret

    def list_content(self, widget):
        item = widget.get_selected_item()
        if item:
            item = item.get_data()
            if isinstance(item, Anime):
                self.list_episodes(item)
            elif isinstance(item, Directory):
                self.anime_list_widget.clear_children()
                self.anime_list_widget.set_data(item)
                logging.info("Loading queue")
                for content in item.get_content():
                    if content == item.parent:
                        ItemWidget(self.anime_list_widget, "<- (Back)", content, style=curses.A_NORMAL)
                    else:
                        ItemWidget(self.anime_list_widget, content.get_name(), content)
                self.anime_list_widget.redraw()

    def list_episodes(self, anime):
        episodes = anime.get_episodes()
        collections = anime.get_collections()

        episode_item_text = []
        latest_accessed_episode = None
        latest_accessed_episode_time = 0
        for episode in episodes:
            last_access_time = user_state.get_last_accessed(episode.get_id())
            completed = user_state.get_completed_status(episode.get_id())
            if last_access_time > latest_accessed_episode_time:
                latest_accessed_episode, latest_accessed_episode_time = episode, last_access_time
            episode_item_text.append((episode.get_number(), "\u2713" if completed else "", episode.get_name()))
        episode_item_text = self.tablize(episode_item_text, 3)

        self.episode_list_widget.clear_children()
        current_collection = None
        for episode_text, episode in zip(episode_item_text, episodes):
            if episode.get_collection() != current_collection:
                current_collection = episode.get_collection()
                if current_collection in collections:
                    InactiveItemWidget(self.episode_list_widget, collections[current_collection])
            ItemWidget(self.episode_list_widget, episode_text, episode, default=(episode == latest_accessed_episode))

        self.switch_to("episodes")

    def open_episode(self, widget):
        item = widget.get_selected_item()
        if item:
            episode = item.get_data()
            episode.open()

    def delete_entry(self, widget):
        item = widget.get_selected_item()
        if item:
            entry_to_remove = item.get_data()
            directory_to_remove_from = widget.get_data()
            if directory_to_remove_from.delete_entry(entry_to_remove):
                logging.info("Successfully removed from the queue")
                widget.remove_selected()
                widget.redraw()
            else:
                logging.error("Error removing the item")


def main(stdscr):
    stdscr = curses.initscr()
    curses.start_color()
    curses.curs_set(0)
    stdscr.keypad(True)
    curses.use_default_colors()

    app = MyApp(stdscr)
    app.run()


if __name__ == '__main__':
    curses.wrapper(main)
