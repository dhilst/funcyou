from typing import Dict, Any, NamedTuple, Optional, Callable, TypedDict
from pyparsing import (  # type: ignore
    Combine,
    Forward,
    Group,
    Keyword,
    ParseResults,
    Literal,
    LineEnd,
    Word,
    alphanums,
    alphas,
    dblQuotedString,
    delimitedList,
    infixNotation,
    nums,
    oneOf,
    opAssoc,
    restOfLine,
)
from collections import namedtuple


class Term:
    def __repr__(self):
        args = ", ".join(f"{k}={repr(v)}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({args})"

class Lambda(Term):
    def __init__(self, arg, body):
        self.arg = arg
        self.body = body

class Application(Term):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2


def to_lambda(t):
    return Lambda(t.arg, t.body.asList())


def to_application(t):
    return Application(t.e1.asList(), t.e2)


def BNF():
    """
    𝑇𝑒𝑟𝑚 → 𝐴𝑏𝑠
    𝑇𝑒𝑟𝑚 → 𝐴𝑝𝑝
    𝐴𝑏𝑠 →𝜆 𝑖𝑑 . 𝑇𝑒𝑟𝑚
    𝐴𝑝𝑝 → 𝑉𝑎𝑟 𝐴𝑝𝑝𝑆𝑒𝑞
    𝐴𝑝𝑝𝑆𝑒𝑞 →𝐴 𝑝𝑝
    𝐴𝑝𝑝𝑆𝑒𝑞 → 𝜖
    𝑉𝑎𝑟 → 𝑖𝑑
    𝑉𝑎𝑟 → ( 𝑇𝑒𝑟𝑚 )
    """

    ID = Word(alphas, exact=1)
    FN = Literal("fn").suppress()
    ARROW = Literal("=>").suppress()
    LP = Literal("(").suppress()
    RP = Literal(")").suppress()

    term = Forward()
    applseq = Forward()

    var = ID | LP + term + RP

    abst = FN + ID("arg") + ARROW + term[1, ...]("body")
    appl = var("e1") + applseq("e2")
    applseq <<= term

    term <<= abst | appl | var

    abst.setParseAction(to_lambda)
    appl.setParseAction(to_application)

    return term


BNF().runTests(
    """
    (fn a => a a) b
    (fn a => a a) (fn b => b)
    """
)
