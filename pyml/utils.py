class classproperty:
    def __init__(self, getter):
        self.getter = getter

    def __get__(self, obj, klass):
        return self.getter(klass)
