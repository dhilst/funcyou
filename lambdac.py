from typing import (
    Dict,
    Any,
    NamedTuple,
    Optional,
    Callable,
    TypedDict,
    Generic,
    TypeVar,
    Iterable,
    Sequence,
    Tuple,
)
from pyparsing import (  # type: ignore
    Combine,
    Empty,
    Forward,
    Group,
    Keyword,
    LineEnd,
    Literal,
    NoMatch,
    ParseResults,
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
    ungroup,
)
from collections import namedtuple
from functools import reduce
from pprint import pprint

T = TypeVar("T")


def pairs(it: Sequence[T]) -> Iterable[Tuple[T, T]]:
    """
    >>> list(pairs([1,2,3,4]))
    [(1, 2), (2, 3), (3, 4)]

    >>> list(pairs([1]))
    []

    >>> list(pairs([]))
    []
    """
    it_ = iter(it)
    a = next(it_, None)
    if a is None:
        return
    for b in it_:
        yield a, b
        a = b


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
    return Lambda(t.arg, t.body.asList()[0])


def to_application(t):
    # Left associativity
    return reduce(Application, t)


def BNF():
    ID = Word(alphas, exact=1)
    FN = Literal("fn").suppress()
    ARROW = Literal("=>").suppress()
    LP = Literal("(").suppress()
    RP = Literal(")").suppress()

    comment = Literal("#").suppress() + restOfLine

    term = Forward()
    appl_ = Forward()

    # abst ::= "fn" ID "=>" term+
    abst = FN + ID("arg") + ARROW + term[1, ...]("body")

    var = ID | LP + term + RP

    appl_ <<= var + appl_[...]  # applseq("e2")
    appl = appl_ | NoMatch()  # add no match to create a new rule

    term <<= abst | appl | var

    term.ignore(comment)
    abst.setParseAction(to_lambda)
    appl.setParseAction(to_application)

    term.validate()

    return term


BNF().runTests(
    """
    # Simple abstraction
    fn a => a a b

    # Chainned abstraction
    fn a => fn b => a b

    # Abstraction application
    (fn a => a a) (fn b => b)

    # Try left associativity of appliction
    a b c d e
    """
)
