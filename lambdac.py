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


T = TypeVar("T", bound="Term")
V = TypeVar("V", bound="Variable")


class Term(ABC):
    """
    Base class for Variable, Abstraction and Application
    """

    def __repr__(self):
        args = ", ".join(f"{k}={repr(v)}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({args})"

    @abstractmethod
    def bind(self, other: "Variable") -> "Term":
        "Should returns the new bound term"
        pass


class Variable(Term, ABC):
    """
    Base class for variables, an variable may be BoundVariable or FreeVariable
    """

    def __init__(self, name: str):
        self.name = name

    def bind(self, other: "Variable") -> "Variable":
        """
        Return the bound variable if the names matches

        The caller should assign the return value where appropriate
        """
        if self.name == other.name:
            return other
        else:
            return self


class FreeVariable(Variable):
    """
    Free variable, call bind_to to bind it
    """

    def __init__(self, name: str):
        super().__init__(name)

    def bind_to(self, lambda_: "Lambda") -> "BoundVariable":
        return BoundVariable(self.name, lambda_)

    def __repr__(self):
        return f"FV({self.name})"


class BoundVariable(Variable):
    """
    Bound variable, use bound to get the lambda to where this variable is bounded
    """

    def __init__(self, name: str, lambda_: "Lambda"):
        super().__init__(name)
        self._bound = lambda_

    @property
    def bound(self):
        return self._bound

    def __repr__(self):
        return f"BV({self.name})"


class Lambda(Term):
    """
    An abstraction, arg is the sole argument and body another Term
    """

    def __init__(self, arg, body: Term):
        self.arg = arg.bind_to(self)
        self.body = body.bind(self.arg)

    def bind(self, var: Variable) -> "Lambda":
        """
        Bind an variable inside body, for example if
        you have (fn a => fn b => a b), fn b => b
        is constructed as Lambda(b, FV(a) BV(b)), then
        fn a => .. calls bind on its argument and we get
        Lambda(a, Lambda(b, BV(a) BV(b)))
        """
        self.body = self.body.bind(var)
        return self

    def __repr__(self):
        return f"(λ{self.arg.name}.{self.body})"


class Application(Term):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def alpha_conversion(self, a, b):
        return Application(
            self.e1.alpha_conversion(a, b), self.e2.alpha_conversion(a, b)
        )

    def bind(self, var: Variable) -> "Application":
        self.e1 = self.e1.bind(var)
        self.e2 = self.e2.bind(var)
        return self

    def __repr__(self):
        return f"{self.e1} {self.e2}"


def to_lambda(t):
    return Lambda(t.arg, t.body.asList()[0])


def to_application(t):
    # Left associativity
    return reduce(Application, t)


def to_variable(t):
    return FreeVariable(t[0])


def BNF():
    if hasattr(BNF, "cache"):
        return BNF.cache
    ID = Word(alphas, exact=1).setParseAction(to_variable)
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

    BNF.cache = term

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
