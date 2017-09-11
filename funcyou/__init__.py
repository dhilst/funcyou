# Copyright 2017 Daniel Hilst Selli
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License. 
# 

'''
Function cheats that I keep below the sleeve.
'''

from functools import partial, reduce
import operator as o 

def compose(*funcs):
    'Return compositon of funcs'
    def compose2(f, g):
        return lambda *args, **kwargs: f(g(*args, **kwargs))
    return reduce(compose2, funcs)

def curry(f):
    'Return curried version of f'
    def _(arg):
        try:
            return f(arg)
        except TypeError:
            return curry(partial(f, arg))
    return _

def fswap(f):
    'Given f(a,b) returns f(b,a)'
    return lambda a,b: f(b,a)

class Let:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __setattr__(self, attr, val):
        raise AttributeError("Can't assing values to Let")


class Pipe:
    def __init__(self, val):
        self.val = val

    def __call__(self):
        return self.val

    def __or__(self, other):
        return Pipe(other(self.val))

#a = Pipe([1,2,3,4]) | sum | (lambda x:x*x) | (lambda x:range(x)) | list
#print(a())

from functools import partial, reduce
class Composition:
    def __init__(self):
        self.funcs = []

    def __call__(self, *args, **kwargs):
        # Refactor this
        return reduce(lambda f, g: lambda *a, **k: f(g(*a,*k)), reversed(self.funcs))(*args, **kwargs)

    def __or__(self, other):
        self.funcs.append(other)
        return self

#f = Composition() | sum | (lambda x:x*x) | (lambda x:range(x)) | list
#print(f([1,2,3,4]))


class _Lambda(object):

    def __init__(self, partial_, swap, symb):
        self.partial = partial_
        self.swap = swap
        self.symb = symb

    def __call__(self, *args, **kwargs):
        return self.partial(*args, **kwargs)

    def __repr__(self):
        repr_ = '({} {} {})'.format(
                        repr(self.partial.args[0]) if not self.swap else '_',
                        self.symb,
                        repr(self.partial.args[0]) if self.swap else '_')
        return repr_ 

def operator_fcty(op, other, swap=False, symb='?'):
    'Operator factory'
    op = fswap(op) if swap else op
    return _Lambda(partial(op, other), swap, symb)

class Lambda(object):
    'Lambda expressions'

    def __le__(self, other):
        return operator_fcty(o.le, other, True, '<=')

    def __lt__(self, other):
        return operator_fcty(o.lt, other, True, '<')

    def __gt__(self, other):
        return operator_fcty(o.gt, other, True)

    def __ge__(self, other):
        return operator_fcty(o.ge, other, True)

    def __rle__(self, other):
        return operator_fcty(o.le, other)

    def __rlt__(self, other):
        return operator_fcty(o.lt, other)

    def __rgt__(self, other):
        return operator_fcty(o.gt, other)

    def __rge__(self, other):
        return operator_fcty(o.ge, other)

    def __eq__(self, other):
        return operator_fcty(o.eq, other)
    __req__ = __eq__

    def __ne__(self, other):
        return operator_fcty(o.ne, other)
    __rne__ = __ne__

    def __mul__(self, other):
        return operator_fcty(o.mul, other)
    __rmul__ = __mul__

    def __add__(self, other):
        return operator_fcty(o.add, other)
    __radd__ = __add__

    def __sub__(self, other):
        return operator_fcty(o.sub, other, True)
    
    def __rsub__(self, other):
        return operator_fcty(o.sub, other)

    def __rfloordiv__(self, other):
        return operator_fcty(o.floordiv, other)

    def __floordiv__(self, other):
        return operator_fcty(o.floordiv, other, True)

    def __rtruediv__(self, other):
        return operator_fcty(o.truediv, other)

    def __truediv__(self, other):
        return operator_fcty(o.truediv, other, True)

    def __mod__(self, other):
        return operator_fcty(o.mod, other, True)

    def __rmod__(self, other):
        return operator_fcty(o.mod, other)

    def __pow__(self, other):
        return operator_fcty(o.pow, other, True)

    def __rpow__(self, other):
        return operator_fcty(o.pow, other)

    def __and__(self, other):
        return operator_fcty(o.pow, other, True)

    def __rand__(self, other):
        return operator_fcty(o.pow, other)

    def __or__(self, other):
        return operator_fcty(o.or_, other, True)

    def __ror__(self, other):
        return operator_fcty(o.or_, other)

    def __xor__(self, other):
        return operator_fcty(o.or_, other, True)

    def __rxor__(self, other):
        return operator_fcty(o.or_, other)

    def __rshift__(self, other):
        return operator_fcty(o.rshift, other, True)

    def __rrshift__(self, other):
        return operator_fcty(o.rshift, other)

    def __lshift__(self, other):
        return operator_fcty(o.lshift, other, True)

    def __rlshift__(self, other):
        return operator_fcty(o.lshift, other)

LAMBDA = Lambda()

class Pipe(object):
    ''' Pipe utility class.
      
        You can chain computaions in a shell like form. Ex.:

        >>> from numpy import prod
        >>> from funcyou import Pipe
        >>> # factorial of 5
        >>> res = Pipe() | range(1,6) | prod
        >>> assert res() == 120
        
        `Pipe()` is a wrapping object impementing __or__ method. The
        object value can be passed as sole argument as in `Pipe('foo')`.
        Pipe object is a callable, when called it does return its value. So that:

        >>> foo = Pipe('foo')
        >>> foo() == 'foo'
        True

        The __or__ method tries to call the right opeator passing the current
        value to it and return its result encapsuled in a Pipe object. If this
        raises TypeError it returns the right size encapsuled in a Pipe.

        >>> foo = Pipe() | 'foo'
        >>> foo() == 'foo'
        True
        
        With this behavior is expected that any amount of expressions can be
        chained and the result can be retrived by calling the return callable.
    ''' 

    def __init__(self, value=None):
        self.value = value

    def __call__(self):
        return self.value
    
    def __or__(self, other):
        try:
            return Pipe(other(self()))
        except TypeError:
            return Pipe(other)

