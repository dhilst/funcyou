import sys
from abc import ABC, abstractmethod
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
    ParserElement,
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


_bound_vars = set()


def _next_var(v: str):
    """
    Return the next letter

    >>> _next_var("u")
    'v'

    >>> _next_var("z")
    'u'
    """
    global _bound_vars
    first = ord("u")
    last = ord("z")
    index = ord(v)
    while True:
        next_ = ord(v) + 1
        if next_ > last:
            next_ = first
        found = chr(next_)
        if found not in _bound_vars:
            return chr(next_)


def _reset_bound_vars():
    global _bound_vars
    _bound_vars = set()


def _bind(var: str):
    _bound_vars.add(var)


class Term:
    ...


class Lamb(Term):
    def __init__(self, var: str, body):
        self.var = var
        self.body = body
        _bind(var)

    def replace(self, old, new):
        if new == self.var:
            # alpha conversion
            old_var = self.var
            self.var = _next_var(self.var)
            self.body = self.body.replace(old_var, self.var)
        self.body = self.body.replace(old, new)
        return self

    def __repr__(self):
        return f"(λ{self.var}.{self.body})"


class Appl(Term):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def replace(self, old, new):
        self.e1 = self.e1.replace(old, new)
        self.e2 = self.e2.replace(old, new)
        return self

    def __repr__(self):
        return f"{self.e1} {self.e2}"


def appl(lam: "Lamb", var: str):
    """
    >>> appl(Lamb("x", "x"), "1")
    '1'
    >>> appl(Lamb("x", Lamb("y", Appl("x", "y"))), "1")
    (λy.1 y)
    >>> appl(Lamb("x", Lamb("y", Appl("x", "y"))), "y")
    (λz.y z)
    """
    _reset_bound_vars()
    return lam.replace(lam.var, var).body


def BNF() -> ParserElement:
    """
   Our grammar
   """
    if hasattr(BNF, "cache"):
        return BNF.cache  # type: ignore

    def to_lambda(t):
        return Lamb(t.arg, t.body.asList()[0])

    def to_application(t):
        # Left associativity
        return reduce(Appl, t)

    def to_variable(t) -> str:
        return t[0]

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
    ID.setParseAction(to_variable)
    abst.setParseAction(to_lambda)
    appl.setParseAction(to_application)

    term.validate()

    BNF.cache = term  # type: ignore

    return term


if __name__ == "__main__":
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

       # Simple application
       (fn a => a) b

       # ɑ conversion needed
       (fn x => x y) y
       """
    )
