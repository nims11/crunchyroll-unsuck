import subprocess
import curses
import os
from gui import InputHandler, ItemWidget, BrowserWidget, ContainerWidget, LogWidget
from gui import BaseLayout, HorizontalLayout, VerticalLayout, Value, App
from api.crunchyroll import CrunchyrollAPI

stdscr = curses.initscr()
api = CrunchyrollAPI()

class MyInputHandler(InputHandler):
    def __init__(self, anime_list_widget, episode_list_widget):
        super().__init__()
        self.anime_list_widget = anime_list_widget
        self.episode_list_widget = episode_list_widget
        self.focused_widget = self.anime_list_widget

    def switch_active_widget(self):
        if self.focused_widget == self.anime_list_widget:
            self.focused_widget = self.episode_list_widget
        elif self.focused_widget == self.episode_list_widget:
            self.focused_widget = self.anime_list_widget

    def tablize(self, rows, extra_padding):
        ret = []
        offset = []
        prev_offset = 0
        for col in range(len(rows[0])):
            offset.append(0)
            for row in rows:
                ret.append('')
                offset[-1] = max(offset[-1], prev_offset + len(row[col]) + extra_padding)
            prev_offset = offset[-1]

        for col in range(len(rows[0])):
            for idx, row in enumerate(rows):
                ret[idx] += row[col]
                if col != len(rows[0])-1:
                    ret[idx] += ' ' * (offset[col] - len(ret[idx]))

        return ret

    def list_episodes(self):
        selected_item = self.anime_list_widget.get_selected_item()
        if selected_item == None:
            return

        anime = selected_item.get_data()
        self.app.log('Fetching episodes...')
        episodes = api.list_media(series_id=anime['series']['series_id'], sort='desc', limit=50)
        self.app.log('Fetched %d episodes' % len(episodes))
        episode_item_text = []
        for episode in episodes:
            episode_item_text.append((episode['episode_number'], episode['name']))
        episode_item_text = self.tablize(episode_item_text, 5)

        self.episode_list_widget.clear_children()
        for episode_text, episode in zip(episode_item_text, episodes):
            ItemWidget(self.episode_list_widget, episode_text, episode)
        self.episode_list_widget.redraw()
        self.focused_widget = self.episode_list_widget

    def open_episode(self):
        selected_item = self.episode_list_widget.get_selected_item()
        if selected_item == None:
            return
        episode = selected_item.get_data()
        args = [
            'streamlink', episode['url'], 'best', '--verbose-player', "-a",
            "--term-status-msg \"Playback Status: ${{time-pos}}\" {filename}"
        ]
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.app.log('$ ' + ' '.join(args))
        for line in p.stdout:
            self.app.log(line.decode())
        p.wait()

    def run(self):
        while True:
            ch = self.app.stdscr.getkey()
            if ch == 'j' or ch == "KEY_DOWN":
                if isinstance(self.focused_widget, BrowserWidget):
                    self.focused_widget.down()
            elif ch == 'k' or ch == "KEY_UP":
                if isinstance(self.focused_widget, BrowserWidget):
                    self.focused_widget.up()
            elif ch == 'l' or ch == "KEY_RIGHT":
                self.switch_active_widget()
            elif ch == 'h' or ch == "KEY_LEFT":
                self.switch_active_widget()
            elif ch == '\n':
                if self.focused_widget == self.anime_list_widget:
                    self.list_episodes()
                elif self.focused_widget == self.episode_list_widget:
                    self.open_episode()


def main(stdscr):
    curses.curs_set(0)
    stdscr.keypad(True)
    curses.use_default_colors()
    root = BaseLayout(Value(curses.COLS), Value(curses.LINES), None)

    l4 = VerticalLayout(Value(1, Value.VAL_RELATIVE), Value(1, Value.VAL_RELATIVE), root)

    l1 = HorizontalLayout(Value(1, Value.VAL_RELATIVE), Value(0.8, Value.VAL_RELATIVE), l4)
    l2 = BaseLayout(Value(0.3, Value.VAL_RELATIVE), Value(1, Value.VAL_RELATIVE), l1)
    l3 = BaseLayout(Value(0.7, Value.VAL_RELATIVE), Value(1, Value.VAL_RELATIVE), l1)

    l5 = BaseLayout(Value(1, Value.VAL_RELATIVE), Value(0.2, Value.VAL_RELATIVE), l4)
    c3 = ContainerWidget(l5, True, "Log")

    c1 = ContainerWidget(l2, True, "Anime")
    c2 = ContainerWidget(l3, True, "Episodes")
    lst1 = BrowserWidget(c1)
    lst2 = BrowserWidget(c2)

    anime_queue = api.get_queue('anime')
    for anime in anime_queue:
        ItemWidget(lst1, anime['series']['name'], anime)

    app = App(stdscr, MyInputHandler(lst1, lst2))
    app.add_workspace('main', root)
    app.set_log_widget(LogWidget(c3))
    app.run()

curses.wrapper(main)
