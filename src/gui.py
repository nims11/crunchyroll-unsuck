""" My kawaii curses framework
"""
# pylint: disable=too-few-public-methods
import curses
import signal

class Value(object):
    """ Size abstraction
    """
    VAL_ABSOLUTE = 'absolute'
    VAL_RELATIVE = 'relative'
    VAL_TYPES = [VAL_ABSOLUTE, VAL_RELATIVE]
    def __init__(self, value, val_type=VAL_ABSOLUTE):
        if val_type not in Value.VAL_TYPES:
            raise Exception("Invalid val_type")
        self.value = value
        self.type = val_type


class BaseObject(object):
    """ Base object which can be redrawn
    """
    def send_event(self, ev):
        pass

    def redraw(self):
        """ define how to draw this object
        """
        pass


class InputHandler(object):
    """ Handles interaction with the App
    """
    def __init__(self):
        self.app = None

    def set_app(self, app):
        self.app = app

    def run(self):
        while True:
            self.app.stdscr.getkey()


class App(object):
    def __init__(self, stdscr, root):
        self.stdscr = stdscr
        self.root = root
        self.root.set_app(self)
        self.log_widget = None
        self.control_object = None
        self.callbacks = {}

    def resize(self, *args, **kwargs):
        y, x = self.stdscr.getmaxyx()
        if y == self.root.height.value and x == self.root.width.value:
            return
        curses.resizeterm(y, x)
        self.stdscr.refresh()
        self.root.width = Value(x)
        self.root.height = Value(y)
        self.root.redraw()

    def set_log_widget(self, widget):
        self.log_widget = widget

    def log(self, msg):
        self.log_widget.update(msg)

    def clear_log(self, msg):
        self.log_widget.clear()

    def set_control(self, obj):
        self.control_object = obj
        for callback in self.callbacks.get('on_set_control', []):
            callback()

    def run(self):
        self.root.redraw()
        while True:
            ch = self.stdscr.getkey()
            if ch == "KEY_RESIZE":
                self.resize()
            elif self.control_object:
                self.control_object.send_event(ch)

    def register_callback(self, event, callback):
        if event not in self.callbacks:
            self.callbacks[event] = []
        self.callbacks[event].append(callback)


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
        self.event_processor = {}
        self.children = []
        self.app = None
        self.focused = True
        if parent != None:
            self.parent.add_child(self)

    def register_event(self, event, ev_processor):
        """ Sets event processor which is called by the send_event
        the processor should return true if the event
        should be propagated"""
        self.event_processor[event] = ev_processor

    def unregister_event(self, event, ev_processor):
        if event in self.event_processor:
            del self.event_processor[event]

    def set_app(self, app):
        if self.parent:
            raise Exception("You can only set app for the root")
        self.app = app

    def get_app(self):
        if not self.app:
            self.app = self.parent.get_app()
        return self.app

    def send_event(self, ev):
        ret = False
        if ev in self.event_processor:
            ret = self.event_processor[ev]()
            if ret and self.parent:
                self.parent.send_event(ev)
        elif self.parent:
            self.parent.send_event(ev)

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

    def focus(self):
        self.focused = True
        for child in self.children:
            child.focus()

    def unfocus(self):
        self.focused = False
        for child in self.children:
            child.unfocus()


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
            child.compute_dimensions(self._height, self._width - cumulative_width, self._x + cumulative_width, self._y)
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
            child.compute_dimensions(self._height - cumulative_height, self._width, self._x, self._y + cumulative_height)
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
    def __init__(self, parent, border=False, title=None, center=False, style=curses.A_NORMAL):
        super().__init__(parent)
        self.window = None
        self.title = title
        self.border = border
        self.style = style
        self.center = center

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

        if self.title:
            if self.center:
                centered_text = self.title.center(self._width, ' ')
                self.window.addstr(0, (len(centered_text) - len(self.title))//2, self.title, self.style)
            else:
                self.window.addstr(0, 0, self.title, self.style)
        self.window.refresh()

        for child in self.children:
            if self.border:
                child.compute_dimensions(self._height-2, self._width-2, self._x+1, self._y + 1)
            elif self.title:
                child.compute_dimensions(self._height-1, self._width-1, self._x, self._y + 1)
            else:
                child.compute_dimensions(self._height, self._width, self._x, self._y)
            child.redraw()


class InactiveItemWidget(Widget):
    def __init__(self, parent, text):
        super().__init__(parent)
        self.text = text

    def redraw(self):
        window = curses.newwin(self._height, self._width, self._y, self._x)
        window.addstr(0, 0, self.get_display_text(self.text, self._width - 4).center(self._width - 1, '-'), curses.A_NORMAL if self.focused else curses.A_DIM)
        window.refresh()


class ItemWidget(Widget):
    def __init__(self, parent, text, data=None, default=False):
        self.text = text
        self._selected = False
        self.data = data
        self.default = default
        super().__init__(parent)

    def redraw(self):
        window = curses.newwin(self._height, self._width, self._y, self._x)
        if self._selected:
            attr = curses.A_REVERSE
            if not self.focused:
                attr |= curses.A_DIM
            window.bkgd(' ', attr)
            window.addstr(0, 0, self.get_display_text(self.text, self._width - 4), attr)
        else:
            window.addstr(0, 0, self.get_display_text(self.text, self._width - 4), curses.A_NORMAL if self.focused else curses.A_DIM)
        window.refresh()

    def select(self):
        self._selected = True

    def unselect(self):
        self._selected = False

    def get_data(self):
        return self.data


class BrowserWidget(Widget):
    def __init__(self, parent):
        super().__init__(parent)
        self.children = []
        self.pos = -1
        self.select_callback = None
        self.register_event('j', self.down)
        self.register_event('k', self.up)
        self.register_event('KEY_DOWN', self.down)
        self.register_event('KEY_UP', self.up)
        self.register_event('\n', self.call_selection_callback)

    def set_selection_callback(self, ev):
        self.select_callback = ev

    def call_selection_callback(self):
        if self.get_selected_item() and self.select_callback:
            self.select_callback(self.get_selected_item())

    def add_child(self, child):
        self.children.append(child)
        if isinstance(child, ItemWidget) and child.default and self.pos < 0:
            self.pos = len(self.children) - 1

    def clear_children(self):
        self.children = []
        self.pos = -1

    def redraw(self):
        window = curses.newwin(self._height, self._width, self._y, self._x)
        window.refresh()
        if self.pos < 0:
            for idx, child in enumerate(self.children):
                if isinstance(child, ItemWidget):
                    self.pos = idx
                    break

        if self.pos >= 0:
            self.children[self.pos].select()
        extra_padding = int(0.5 * self._height)
        start = max(min(len(self.children) - self._height, self.pos - extra_padding), 0)
        for idx, child in enumerate(self.children[start:start+self._height]):
            child.compute_dimensions(1, self._width, self._x, idx + self._y)
            child.redraw()
        curses.doupdate()

    def up(self):
        next_pos = self.pos - 1
        while next_pos >= 0 and not isinstance(self.children[next_pos], ItemWidget):
            next_pos -= 1
        if next_pos >= 0:
            self.children[self.pos].unselect()
            self.pos = next_pos
            self.redraw()

    def down(self):
        next_pos = self.pos + 1
        while next_pos < len(self.children) and not isinstance(self.children[next_pos], ItemWidget):
            next_pos += 1
        if next_pos < len(self.children):
            self.children[self.pos].unselect()
            self.pos = next_pos
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
        self.lines.append(line.strip())
        if len(self.lines) > self.buffer_size:
            self.lines = self.lines[-self.buffer_size:]
        self.redraw()

    def clear(self):
        self.lines = []
        self.redraw()

    def redraw(self):
        window = curses.newwin(self._height, self._width, self._y, self._x)
        for idx, line in enumerate(self.lines[-self._height:]):
            window.addnstr(idx, 0, self.get_display_text(line, self._width - 4), self._width)
        window.refresh()


class ShortcutWidget(Widget):
    def __init__(self, parent, event_parent, shortcuts=[]):
        super().__init__(parent)
        self.shortcuts = []
        self.event_parent = event_parent
        self.replace_shortcuts(shortcuts)

    def replace_shortcuts(self, shortcuts):
        for (shortcut, _, _) in self.shortcuts:
            self.event_parent.unregister_event(shortcut)
        self.shortcuts = shortcuts
        for (shortcut, description, callback) in self.shortcuts:
            self.event_parent.register_event(shortcut, callback)

    def redraw(self):
        window = curses.newwin(self._height, self._width, self._y, self._x)
        display_text = ''
        for shortcut, description, callback in self.shortcuts:
            if len(display_text + shortcut + ':' + description) <= self._width:
                display_text += shortcut + ':' + description + '  '
            else:
                break
        window.addnstr(0, 0, display_text.strip(), self._width)
        window.refresh()
