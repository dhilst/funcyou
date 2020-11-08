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


T = TypeVar("T", bound="Term")
V = TypeVar("V", bound="Variable")


def next_var(v: str):
    """
    Return the next letter

    >>> next_var("a")
    'b'

    >>> next_var("z")
    'a'
    """
    first = ord("a")
    last = ord("z")
    index = ord(v)
    next_ = ord(v) + 1
    if next_ > last:
        next_ = first
    return chr(next_)


class AlphaConversionException(Exception):
    pass


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

    @abstractmethod
    def has_freevar_named(self, name: str) -> bool:
        "Should return true if free variable with name @name is found"
        pass

    def to_str(self):
        return repr(self)


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

    def release(self, varname: str):
        if self.name == varname:
            return FreeVariable(self.name)
        return self


class FreeVariable(Variable):
    """
    Free variable, call bind_to to bind it
    """

    def __init__(self, name: str):
        super().__init__(name)

    def bind_to(self, lambda_: "Lambda") -> "BoundVariable":
        return BoundVariable(self.name, lambda_)

    def has_freevar_named(self, name: str) -> bool:
        return self.name == name

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

    def rename(self, to: str):
        self.name = to

    def has_freevar_named(self, name: str) -> bool:
        return False

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

    def alpha_conversion(self, to: str):
        """
        Run an alpha conversion (λx.x) -> (λy.y)

        Construct an expression
        >>> x = FreeVariable("x")
        >>> y = FreeVariable("y")
        >>> l1 = Lambda(x, Application(x, y))

        Check that it's what we expect
        >>> repr(l1)
        '(λx.BV(x) FV(y))'

        Do alpha conversion and check it again
        >>> l1.alpha_conversion("z")
        >>> repr(l1)
        '(λz.BV(z) FV(y))'

        '(λz.BV(x)) FV(y) => FV(y)'

        Trying to alhpa-convert raise an error if the free variable is already
        taken
        >>> l1.alpha_conversion("y")
        Traceback (most recent call last):
        lambdac.AlphaConversionException: FV(y) present in BV(z) FV(y), cant ɑ-convert
        """
        if self.has_freevar_named(to):
            raise AlphaConversionException(
                f"FV({to}) present in {self.body}, cant ɑ-convert"
            )
        self.arg.rename(to)

    def cbv(self, arg: Term) -> Term:
        """
        (λx.x) y                        => a = Application(e1=Lambda(arg=BV(x), body=BV(x)), e2=FV(y))
            -> x{y/x}                   => a.eval() => a.e1.replace(a.e2)
            -> y                        => FV(y)

        (λx.x x) y                      => a = Appl(Lam(x, Appl(x, x)), y)
            -> (x x){y/x}               => a.eval() => a.e1.replace(a.e2)
            -> (y y)                    => Appl(y, y)

        (λx.λy.y x) (λx.1)              => a = App(Lam(x, Lam(y, Appl(y, x))), Lam(x, 1)); a.eval()
            -> (λy.y x){λx.1/x}         => a.e1.replace(a.e2)
            -> (λy.y (λx.1))            => Lam(y, App(y, Lam(x, 1)))

        (λx.λy.x y) y                   => a = Appl(Lam(x, Lam(y, Appl(x, y))), y); a.eval()
            -> (λy.x y){x/y}            => a.e1.replace(a.e2) => throws CaptureException(y)
            -> ((λx.x y){NX()/y}){x/y}  => a.e1.replace(NX() => z, ex.var => y).replace(a.e2)
            -> (λx.x z){x/y}            => a.e1.replace(a.e2)
            -> (λx.y z)                 => Lam(y, z)

        """
        arg = arg.eval()
        return self.body.cbv(arg)

    def call(self, arg: Variable):
        """
        Beta reduction

        '(λz.BV(x)) FV(y) => FV(y)'.repl



        (λx.λz.y z)
            -> (λa.λz.y a)

        (λx.λz.y x) y
            -> (λz.y x){x/y}        (variable FV(y) captured)
            -> ((λz.y x){a/y}){x/y} (rename FV(y) -> FV(a)){
            -> (λz.a x){x/y}
            -> (λz.a y)

        (λx.λz.y x) y
            -> (λz.y x){x/y}        (variable FV(y) captured)
            -> (λz.y x)({x/y}{y/NV(x,y,z)}) (rename outer FV(y) -> FV(a)
            -> (λz.y x)({x/y}{y/a}) (rename outer FV(y) -> FV(a)
            -> (λz.y x){x/a}
            -> (λz.y a)


        (λz.a y) -> λ.1 2
        (λz.y a) -> λ.1 2

        (λx.srqt(x) + 1) 4
            -> (sqrt(x) + 1){4/x}
            -> sqrt(4) + 1
            -> 2 + 1
            -> 1


        (λx.x y) y
        (λx.λy.y z) z
            -> [x -> z](λy.y z)
            -> (λy.y z) z
            -> [y -> z]y z
            -> [y -> a]y z
            -> a z

        (λx.x)
            -> [x -> z](λx.x)
            -> λz.z

        (λx.λy.z y) z
            -> [x -> z]λy.z y
            -> λy.z y

        >>> x = FreeVariable("x")
        >>> y = FreeVariable("y")
        >>> z = FreeVariable("z")

        # ID function
        >>> l = Lambda(x, x)
        >>> res = l.call(y)
        >>> repr(res)
        'FV(y)'

        Replace on application
        >>> l = Lambda(x, Application(x, z))
        >>> res = l.call(y)
        >>> repr(res)
        'FV(y) FV(z)'

        Contant function
        >>> Lambda(x, y).call(z).to_str()
        'FV(y)'

        Alpha conversion done
        (λx.x y) y => z y
        >>> Lambda(x, Application(x,y)).call(y).to_str()
        'FV(z) FV(y)'
        """
        if self.has_freevar_named(arg.name):
            next_ = self.next_var(arg.name)
            self.alpha_conversion(next_)
        if isinstance(self.body, BoundVariable):
            return arg
        elif isinstance(self.body, FreeVariable):
            return self.body
        elif isinstance(self.body, Application):
            if self.has_freevar_named(arg.name):
                return self.body.release(self.arg.name)
            if self.body.e1.name == self.arg.name:
                self.body.e1 = arg
            if self.body.e2.name == self.arg.name:
                self.body.e2 = arg
            return self.body

    def next_var(self, var: str) -> str:
        count = 0
        while self.has_freevar_named(var):
            var = next_var(var)
            count += 1
            if count > 26:
                raise RuntimeError("no more variables available")
        return var

    def has_freevar_named(self, name: str) -> bool:
        return self.body.has_freevar_named(name)

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

    def has_freevar_named(self, name: str) -> bool:
        return self.e1.has_freevar_named(name) or self.e2.has_freevar_named(name)

    def __repr__(self):
        return f"{self.e1} {self.e2}"

    def release(self, varname: str):
        return Application(self.e1.release(varname), self.e2.release(varname))


def BNF() -> ParserElement:
    """
    Our grammar
    """
    if hasattr(BNF, "cache"):
        return BNF.cache  # type: ignore

    def to_lambda(t):
        return Lambda(t.arg, t.body.asList()[0])

    def to_application(t):
        # Left associativity
        return reduce(Application, t)

    def to_variable(t):
        return FreeVariable(t[0])

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
