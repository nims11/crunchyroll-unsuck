import sys
import curses

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
        self.log_widget = None

    def add_workspace(self, name, root, default=False):
        self.workspaces[name] = root
        if default or len(self.workspaces) == 1:
            self.current_workspace = name

    def set_workspace(self, name):
        self.current_workspace = name
        self.workspaces[self.current_workspace].redraw()

    def set_log_widget(self, widget):
        self.log_widget = widget

    def log(self, msg):
        self.log_widget.update(msg)

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

    def get_display_text(self, text, width):
        """ Truncates if there is a chance of overflow. Don't use tabs, it breaks things
        """
        if len(text) > width:
            return text[:width] + '...'
        return text


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
            window.addstr(0, 0, self.get_display_text(self.text, self._width - 3), curses.A_REVERSE)
        else:
            window.addstr(0, 0, self.get_display_text(self.text, self._width - 3))
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


class LogWidget(Widget):
    def __init__(self, parent, buffer_size=25):
        super().__init__(parent)
        self.lines = []
        self.buffer_size = buffer_size

    def update(self, line):
        self.lines.append(line)
        if len(self.lines) > self.buffer_size:
            self.lines = self.lines[-self.buffer_size:]
        log(str(self.lines))
        self.redraw()

    def redraw(self):
        for idx, line in enumerate(self.lines[-self._height:]):
            window = curses.newwin(self._height, self._width, self._y, self._x)
            window.addstr(idx, 0, self.get_display_text(line, self._width))
