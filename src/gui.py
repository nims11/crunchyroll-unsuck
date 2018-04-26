import curses

class Value(object):
    VAL_ABSOLUTE = 'absolute'
    VAL_RELATIVE = 'relative'
    VAL_TYPES = [VAL_ABSOLUTE, VAL_RELATIVE]
    def __init__(self, value, val_type='absolute'):
        if val_type not in Value.VAL_TYPES:
            raise Exception("Invalid val_type")
        self.value = value
        self.val_type = val_type


class BaseObject(object):
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
        self.parent = parent
        self.children = []
        if parent != None:
            self.parent.add_child(self)


    def add_child(self, child):
        if self.children:
            raise Exception("BaseLayout cannot have more than one children")
        self.children.append(child)


    def redraw(self):
        if self.height.val_type == Value.VAL_ABSOLUTE:
            self._height = int(self.height.value)

        if self.width.val_type == Value.VAL_ABSOLUTE:
            self._width = int(self.width.value)

        if self.parent is not None:
            if self.height.val_type == Value.VAL_RELATIVE:
                self._height = int(self.parent._height*self.height.value)
            if self.width.val_type == Value.VAL_RELATIVE:
                self._width = int(self.parent._width*self.width.value)

        elif self.width.type == Value.VAL_RELATIVE or self.height.type == Value.VAL_RELATIVE:
            raise Exception('root layout cannot have relative dimensions')


        for child in self.children:
            child.redraw()


class StackedLayout(BaseLayout):
    """ Stacked Layout. Can contain multiple children
    """
    def add_child(self, child):
        self.children.append(child)


class HorizontalLayout(StackedLayout):
    """ child layouts arranged horizontally
    """
    pass


class VerticalLayout(StackedLayout):
    """ child layouts arranged vertically
    """
    pass


# def main(stdscr):
#     stdscr.clear()

# curses.wrapper(main)
