import sys
import curses

stdscr = curses.initscr()

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


class App(object):
    def __init__(self, root, stdscr):
        self.input_control = None
        self.root = root
        self.root.set_app(self)
        self.stdscr = stdscr


    def run(self):
        self.root.redraw()
        while True:
            c = self.stdscr.getch()
            if self.input_control:
                self.input_control.send_input_ch(c)


    def set_input_control(self, obj):
        self.input_control = obj


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
        self.app = None
        if parent != None:
            self.parent.add_child(self)


    def set_app(self, app):
        if self.parent:
            raise Exception("You can only set app for the root")
        self.app = app


    def get_app(self):
        if not self.app:
            self.app = self.parent.get_app()
        return self.app


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
    def __init__(self, parent, text):
        super().__init__(parent)
        self.text = text
        self._focus = False

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


class BrowserWidget(Widget):
    def __init__(self, parent):
        super().__init__(parent)
        self.window = None
        self.children = []
        self.pos = -1


    def add_child(self, child):
        # if not isinstance(child, item):
        #     raise Exception("ContainerWidget cannot have more than one children")
        self.children.append(child)


    def redraw(self):
        self.get_app().set_input_control(self)
        if len(self.children) > 0 and self.pos < 0:
            self.pos = 0

        self.children[self.pos].focus()
        extra_padding = int(0.5 * self._height)
        start = max(min(len(self.children) - self._height, self.pos - extra_padding), 0)
        for idx, child in enumerate(self.children[start:start+self._height]):
            child.compute_dimensions(1, self._width, self._x, idx + self._y)
            child.redraw()


    def send_input_ch(self, key):
        if chr(key) == 'j':
            if self.pos < len(self.children) - 1:
                self.children[self.pos].unfocus()
                self.pos += 1
                self.redraw()
            return True
        elif chr(key) == 'k':
            if self.pos > 0:
                self.children[self.pos].unfocus()
                self.pos -= 1
                self.redraw()
            return True

        return False


def main(stdscr):
    curses.use_default_colors()
    root = BaseLayout(Value(curses.COLS), Value(curses.LINES), None)
    l1 = HorizontalLayout(Value(1, Value.VAL_RELATIVE), Value(1, Value.VAL_RELATIVE), root)
    l2 = BaseLayout(Value(0.3, Value.VAL_RELATIVE), Value(1, Value.VAL_RELATIVE), l1)
    l3 = BaseLayout(Value(0.7, Value.VAL_RELATIVE), Value(1, Value.VAL_RELATIVE), l1)

    c1 = ContainerWidget(l2, True, "Anime")
    ContainerWidget(l3, True, "Episodes")
    lst = BrowserWidget(c1)
    for i in list(range(-10, 40))[::-1]:
        ItemWidget(lst, str(i))

    App(root, stdscr).run()

curses.wrapper(main)
