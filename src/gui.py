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


class Widget(BaseObject):
    def __init__(self, parent):
        self.parent = parent
        if parent != None:
            self.parent.add_child(self)


    def redraw(self):
        pass


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
        if parent != None:
            self.parent.add_child(self)


    def add_child(self, child):
        if self.children:
            raise Exception("BaseLayout cannot have more than one children")
        self.children.append(child)


    def compute_dimensions(self):
        if self.height.type == Value.VAL_ABSOLUTE:
            self._height = int(self.height.value)

        if self.width.type == Value.VAL_ABSOLUTE:
            self._width = int(self.width.value)

        if self.parent is not None:
            if self.height.type == Value.VAL_RELATIVE:
                self._height = int(self.parent._height*self.height.value)
            if self.width.type == Value.VAL_RELATIVE:
                self._width = int(self.parent._width*self.width.value)
        elif self.width.type == Value.VAL_RELATIVE or self.height.type == Value.VAL_RELATIVE:
            raise Exception('root layout cannot have relative dimensions')
        else:
            self._x = 0
            self._y = 0


    def redraw(self):
        self.compute_dimensions()
        for child in self.children:
            if isinstance(child, BaseLayout):
                child._x = self._x
                child._y = self._y
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
        self.compute_dimensions()
        cumulative_width = 0
        for child in self.children:
            child._x = self._x + cumulative_width
            child._y = self._y
            child.redraw()
            cumulative_width += child._width


class VerticalLayout(StackedLayout):
    """ child layouts arranged vertically
    """
    def redraw(self):
        self.compute_dimensions()
        cumulative_height = 0
        for child in self.children:
            child._x = self._x
            child._y = self._y + cumulative_height
            child.redraw()
            cumulative_height += child._height


class DummyWidget(Widget):
    def __init__(self, parent):
        super().__init__(parent)
        self.window = None

    def redraw(self):
        if self.window is not None:
            pass
        self.window = curses.newwin(self.parent._height, self.parent._width, self.parent._y, self.parent._x)
        self.window.border()
        self.window.addstr(0, 0, "%dx%d - (%d,%d)" % (self.parent._height, self.parent._width, self.parent._y, self.parent._x))
        self.window.refresh()


def main(stdscr):
    root = BaseLayout(Value(curses.COLS), Value(curses.LINES), None)
    l1 = VerticalLayout(Value(1, Value.VAL_RELATIVE), Value(1, Value.VAL_RELATIVE), root)
    l2 = BaseLayout(Value(1, Value.VAL_RELATIVE), Value(0.33, Value.VAL_RELATIVE), l1)
    l3 = HorizontalLayout(Value(1, Value.VAL_RELATIVE), Value(0.33, Value.VAL_RELATIVE), l1)
    l4 = BaseLayout(Value(1, Value.VAL_RELATIVE), Value(0.34, Value.VAL_RELATIVE), l1)

    DummyWidget(l2)
    DummyWidget(l4)
    l5 = BaseLayout(Value(0.33, Value.VAL_RELATIVE), Value(1, Value.VAL_RELATIVE), l3)
    l6 = BaseLayout(Value(0.33, Value.VAL_RELATIVE), Value(1, Value.VAL_RELATIVE), l3)
    l7 = BaseLayout(Value(0.34, Value.VAL_RELATIVE), Value(1, Value.VAL_RELATIVE), l3)
    DummyWidget(l5)
    DummyWidget(l6)
    DummyWidget(l7)

    root.redraw()

    stdscr.getkey()

curses.wrapper(main)
