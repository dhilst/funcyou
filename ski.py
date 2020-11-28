from functools import wraps, partial, update_wrapper


class namedpartial:
    def __init__(self, func, *args):
        self.func = func
        self.partial = partial(func, *args)

    def __call__(self, *args):
        return self.partial(*args)

    def __repr__(self):
        return f"{self.partial.func.__name__} {' '.join(map(str, self.partial.args))}"


class curry:
    def __init__(self, func):
        self.func = func

    def __call__(self, *args):
        try:
            return self.func(*args)
        except TypeError as e:
            if "required positional argument" in str(e):
                return namedpartial(self.func, *args)
            raise e

    def __repr__(self):
        return self.func.__name__


@curry
def I(x):
    return x


@curry
def K(x, y):
    return x


@curry
def S(x, y, z):
    yz = y(z)
    xz = x(z)
    return xz(yz)


print(S(K, S, K))
