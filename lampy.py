import ast
import readline
from pyparsing import *

class Value:
    def __init__(self, t):
        self._value = t

    @property
    def value(self):
        return self._value

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.value)


class Identifier(Value):
    pass

class Reserved(Value):
    pass

class Definition(Value):
    def __init__(self, name, parameters, body):
        self.name = name
        self.parameters = parameters 
        self.body = body

    def __repr__(self):
        return '{}({}, {}) -> {}'.format(self.__class__.__name__,
                                      self.name, self.parameters, self.body)

    def __call__(self, *args):
        parargs = {k.value:v for k, v in zip(self.parameters, args)}
        return self.body.eval(**parargs)

env = {}
class Expression(Value):

    def eval(self, **callenv):
        if issubclass(type(self.value[0]), Reserved):
            kw = self.value[0].value
            if kw == 'def':
                name, body, parameters = self.value[1].value, self.value[-1], tuple(self.value[2:-1])
                fun = Definition(name, parameters, body)
                env[name] = fun
                return fun
        elif issubclass(type(self.value[0]), Identifier):
            name = self.value[0].value
            args = []
            for arg in self.value[1:]:
                if issubclass(type(arg), Identifier) and arg.value in callenv:
                    args.append(callenv[arg.value])
                else:
                    args.append(arg)

            if name in env:
                return env[name](*args)
            try:
                return getattr(__builtins__, name)(args)
            except AttributeError:
                pass
        
            raise RuntimeError('Undefined: {}'.format(name))


NUM = Word(nums)

expr  = Forward()
DEF = Keyword('def')
RESERVED = MatchFirst(r for r in (DEF,))
ID = ~RESERVED & Word(alphas)
atom = RESERVED | ID | NUM
LP = Literal('(').suppress()
RP = Literal(')').suppress()
expr << Group(LP + ZeroOrMore(atom | expr) + RP)
exprs =  ZeroOrMore(expr)

@NUM.setParseAction
def parse_NUM(s, l, t):
    return int(t[0])

@ID.setParseAction
def parse_ID(s, l, t):
    return Identifier(t[0])

@RESERVED.setParseAction
def parse_RESERVED(s, l, t):
    return Reserved(t[0])

@expr.setParseAction
def parse(s, l, t):
    return Expression(t[0])

def eval_expr(expr):
    for e in expr:
        print(e.eval())

e = exprs.parseString('(def inc x (sum x 1)) (inc 2) (inc 10)')
eval_expr(e)
