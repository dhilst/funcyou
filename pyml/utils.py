import logging

logger = logging.getLogger("pyml")
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
formatter = logging.Formatter("==> %(levelname)s: %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class classproperty:
    def __init__(self, getter):
        self.getter = getter

    def __get__(self, obj, klass):
        return self.getter(klass)
