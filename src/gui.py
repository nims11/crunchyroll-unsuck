import sys
import curses
import subprocess
from api.crunchyroll import CrunchyrollAPI

stdscr = curses.initscr()
api = CrunchyrollAPI()

logfile = open('/tmp/log', 'w')
def log(msg):
    logfile.write(msg + '\n')


class Value(object):
    VAL_ABSOLUTE = 'absolute'
    VAL_RELATIVE = 'relative'
    VAL_TYPES = [VAL_ABSOLUTE, VAL_RELATIVE]
    def __init__(self, value, val_type=VAL_ABSOLUTE):
        if val_type not in Value.VAL_TYPES:
            raise Exception("Invalid val_type")
        self.value = value
        self.type = val_type


class BaseObject(object):
    def redraw(self):
        pass


class InputHandler(object):
    def run(self, app):
        while True:
            app.stdscr.getkey()


class App(object):
    def __init__(self, stdscr, inputhandler=None):
        self.stdscr = stdscr
        if inputhandler == None:
            inputhandler = InputHandler()
        self.inputhandler = inputhandler
        self.workspaces = {}
        self.current_workspace = None


    def add_workspace(self, name, root, default=False):
        self.workspaces[name] = root
        if default or len(self.workspaces) == 1:
            self.current_workspace = name


    def set_workspace(self, name):
        self.current_workspace = name
        self.workspaces[self.current_workspace].redraw()


    def run(self):
        self.workspaces[self.current_workspace].redraw()
        self.inputhandler.run(self)


class BaseLayout(BaseObject):
    """ Base Layout unit. Can only contain one child
    """
    def __init__(self, width, height, parent):
        self.width = width
        self.height = height
        self._height = None
        self._width = None
        self._x = None
        self._y = None
        self.parent = parent
        self.children = []
        # self.app = None
        if parent != None:
            self.parent.add_child(self)


    # def set_app(self, app):
    #     if self.parent:
    #         raise Exception("You can only set app for the root")
    #     self.app = app


    # def get_app(self):
    #     if not self.app:
    #         self.app = self.parent.get_app()
    #     return self.app


    def add_child(self, child):
        if self.children:
            raise Exception("BaseLayout cannot have more than one children")
        self.children.append(child)


    def compute_dimensions(self, parent_height=None, parent_width=None, parent_x = None, parent_y = None):
        if parent_x == None:
            self._x = 0
        else:
            self._x = parent_x

        if parent_y == None:
            self._y = 0
        else:
            self._y = parent_y

        if self.height.type == Value.VAL_ABSOLUTE:
            self._height = int(self.height.value)

        if self.width.type == Value.VAL_ABSOLUTE:
            self._width = int(self.width.value)

        if self.parent is not None:
            if self.height.type == Value.VAL_RELATIVE:
                self._height = int(parent_height*self.height.value)
            if self.width.type == Value.VAL_RELATIVE:
                self._width = int(parent_width*self.width.value)
        elif self.width.type == Value.VAL_RELATIVE or self.height.type == Value.VAL_RELATIVE:
            raise Exception('root layout cannot have relative dimensions')


    def redraw(self):
        if self.parent == None:
            self.compute_dimensions()
        for child in self.children:
            child.compute_dimensions(self._height, self._width, self._x, self._y)
            child.redraw()


class StackedLayout(BaseLayout):
    """ Stacked Layout. Can contain multiple children
    """
    def add_child(self, child):
        if isinstance(child, BaseLayout):
            self.children.append(child)
        else:
            raise Exception("StackedLayout can only have BaseLayouts as children")


class HorizontalLayout(StackedLayout):
    """ child layouts arranged horizontally
    """
    def redraw(self):
        if self.parent == None:
            self.compute_dimensions()
        cumulative_width = 0
        for child in self.children:
            child.compute_dimensions(self._height, self._width, self._x + cumulative_width, self._y)
            child.redraw()
            cumulative_width += child._width


class VerticalLayout(StackedLayout):
    """ child layouts arranged vertically
    """
    def redraw(self):
        if self.parent == None:
            self.compute_dimensions()
        cumulative_height = 0
        for child in self.children:
            child.compute_dimensions(self._height, self._width, self._x, self._y + cumulative_height)
            child.redraw()
            cumulative_height += child._height


class Widget(BaseLayout):
    def __init__(self, parent):
        super().__init__(None, None, parent)
        if parent == None:
            raise Exception("Widget needs parents")


    def add_child(self, child):
        raise Exception("Widget cannot have children")


    def compute_dimensions(self, parent_height=None, parent_width=None, parent_x = None, parent_y = None):
        self._height = parent_height
        self._width = parent_width
        self._x = parent_x
        self._y = parent_y


    def redraw(self):
        pass


    def send_input_ch(self, key):
        pass


class DummyWidget(Widget):
    def __init__(self, parent):
        super().__init__(parent)
        self.window = None

    def redraw(self):
        if self.window is not None:
            pass
        self.window = curses.newwin(self._height, self._width, self._y, self._x)
        self.window.border()
        self.window.addstr(0, 0, "%dx%d - (%d,%d)" % (self._height, self._width, self._y, self._x))
        self.window.refresh()


class ContainerWidget(Widget):
    def __init__(self, parent, border=False, title=None):
        super().__init__(parent)
        self.window = None
        self.title = title
        self.border = border


    def add_child(self, child):
        if self.children:
            raise Exception("ContainerWidget cannot have more than one children")
        self.children.append(child)


    def redraw(self):
        if self.window is not None:
            del self.window
        self.window = curses.newwin(self._height, self._width, self._y, self._x)
        if self.border:
            self.window.border()
        self.window.addstr(0, 0, self.title)
        self.window.refresh()

        for child in self.children:
            if self.border or self.title:
                child.compute_dimensions(self._height-2, self._width-2, self._x+1, self._y + 1)
            else:
                child.compute_dimensions(self._height, self._width, self._x, self._y)
            child.redraw()


class ItemWidget(Widget):
    def __init__(self, parent, text, data=None):
        super().__init__(parent)
        self.text = text
        self._focus = False
        self.data = data

    def redraw(self):
        window = curses.newwin(self._height, self._width, self._y, self._x)
        if self._focus:
            window.bkgd(' ', curses.A_REVERSE)
            window.addstr(0, 0, self.text, curses.A_REVERSE)
        else:
            window.addstr(0, 0, self.text)
        window.refresh()


    def focus(self):
        self._focus = True


    def unfocus(self):
        self._focus = False


    def get_data(self):
        return self.data


class BrowserWidget(Widget):
    def __init__(self, parent):
        super().__init__(parent)
        self.children = []
        self.pos = -1


    def add_child(self, child):
        # if not isinstance(child, item):
        #     raise Exception("ContainerWidget cannot have more than one children")
        self.children.append(child)


    def clear_children(self):
        self.children = []
        self.pos = -1


    def redraw(self):
        if len(self.children) > 0:
            if self.pos < 0:
                self.pos = 0
        else:
            return

        self.children[self.pos].focus()
        extra_padding = int(0.5 * self._height)
        start = max(min(len(self.children) - self._height, self.pos - extra_padding), 0)
        for idx, child in enumerate(self.children[start:start+self._height]):
            child.compute_dimensions(1, self._width, self._x, idx + self._y)
            child.redraw()


    def up(self):
        if self.pos > 0:
            self.children[self.pos].unfocus()
            self.pos -= 1
            self.redraw()


    def down(self):
        if self.pos < len(self.children) - 1:
            self.children[self.pos].unfocus()
            self.pos += 1
            self.redraw()


    def get_selected_item(self):
        if self.pos >= 0:
            return self.children[self.pos]
        return None


class MyInputHandler(InputHandler):
    def __init__(self, anime_list_widget, episode_list_widget):
        self.anime_list_widget = anime_list_widget
        self.episode_list_widget = episode_list_widget
        self.focused_widget = self.anime_list_widget


    def run(self, app):
        while True:
            ch = app.stdscr.getkey()
            if ch == 'j' or ch == "KEY_DOWN":
                if isinstance(self.focused_widget, BrowserWidget):
                    self.focused_widget.down()
            elif ch == 'k' or ch == "KEY_UP":
                if isinstance(self.focused_widget, BrowserWidget):
                    self.focused_widget.up()
            elif ch == 'l' or ch == "KEY_RIGHT":
                if self.focused_widget == self.anime_list_widget:
                    self.focused_widget = self.episode_list_widget
                elif self.focused_widget == self.episode_list_widget:
                    self.focused_widget = self.anime_list_widget
            elif ch == 'h' or ch == "KEY_LEFT":
                if self.focused_widget == self.anime_list_widget:
                    self.focused_widget = self.episode_list_widget
                elif self.focused_widget == self.episode_list_widget:
                    self.focused_widget = self.anime_list_widget
            elif ch == '\n':
                if self.focused_widget == self.anime_list_widget:
                    selected_item = self.anime_list_widget.get_selected_item()
                    if selected_item != None:
                        anime = selected_item.get_data()
                        episodes = api.list_media(series_id=anime['series']['series_id'], sort='desc')
                        self.episode_list_widget.clear_children()
                        for episode in episodes:
                            ItemWidget(self.episode_list_widget, '%s\t\t%s' % (episode['episode_number'], episode['name']), episode)
                        self.episode_list_widget.redraw()
                        self.focused_widget = self.episode_list_widget
                elif self.focused_widget == self.episode_list_widget:
                    selected_item = self.episode_list_widget.get_selected_item()
                    if selected_item != None:
                        episode = selected_item.get_data()
                        subprocess.call('streamlink \'%s\' best' % episode['url'], shell=True)
                        app.set_workspace('main')


def main(stdscr):
    curses.curs_set(0)
    stdscr.keypad(True)
    curses.use_default_colors()
    root = BaseLayout(Value(curses.COLS), Value(curses.LINES), None)
    l1 = HorizontalLayout(Value(1, Value.VAL_RELATIVE), Value(1, Value.VAL_RELATIVE), root)
    l2 = BaseLayout(Value(0.3, Value.VAL_RELATIVE), Value(1, Value.VAL_RELATIVE), l1)
    l3 = BaseLayout(Value(0.7, Value.VAL_RELATIVE), Value(1, Value.VAL_RELATIVE), l1)

    c1 = ContainerWidget(l2, True, "Anime")
    c2 = ContainerWidget(l3, True, "Episodes")
    lst1 = BrowserWidget(c1)
    lst2 = BrowserWidget(c2)

    anime_queue = api.get_queue('anime')
    for anime in anime_queue:
        ItemWidget(lst1, anime['series']['name'], anime)

    app = App(stdscr, MyInputHandler(lst1, lst2))
    app.add_workspace('main', root)
    app.run()

curses.wrapper(main)
