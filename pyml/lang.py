from typing import *
from pprint import pprint, pformat
from pyparsing import (  # type: ignore
    Forward,
    Combine,
    Word,
    alphanums,
    nums,
    alphas,
    ParseResults,
    restOfLine,
    dblQuotedString,
    infixNotation,
    oneOf,
    opAssoc,
    delimitedList,
)
from collections import namedtuple
from collections.abc import MutableMapping
from abc import ABC, abstractmethod
import operator as op


class classproperty:
    def __init__(self, getter):
        self.getter = getter

    def __get__(self, obj, klass):
        return self.getter(klass)

class ScopeEnv:
    """
    Our environment as nested scopes
    """

    # fmt: off
    _scope: Dict[str, Any] = {
        "+": op.add,
    }
    # fmt: on

    _current = _scope

    @classmethod
    def push(cls, scope: str, key: str, value: Any):
        cls._scope.setdefault(scope, {})[key] = value
        cls._current = cls._scope[scope]

    @classmethod
    def pop(cls, scope: str):
        cls._current = cls._scope

    @classmethod
    def dump(cls) -> str:
        return pformat(cls._scope)

    @classproperty
    def current(cls):
        return cls._current

    @classproperty
    def current_name(cls):
        for k, v in cls._scope:
            if v is cls._current:
                return k
        return "global"

    @classmethod
    def lookup(cls, key) -> Optional[Any]:
        val = cls.current.get(key)
        if val is not None:
            return val
        return cls._scope.get(key)


class Node(ABC):
    @abstractmethod
    def __init__(self, tokens: ParseResults):
        pass

    def __repr__(self):
        attrs = ", ".join(f"{k}={repr(v)}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"


class _TypeUnknow:
    pass


TypeUnknow = _TypeUnknow


class Identifier(Node):
    def __init__(self, tokens: ParseResults):
        self.name = tokens[0]


class Expr(Node):
    def __init__(self, tokens: ParseResults):
        self.value = tokens.value
        self.type = TypeUnknow


class Lookup(Expr):
    def __init__(self, tokens: ParseResults):
        self.varname = tokens.varname
        self.type = TypeUnknow


class Constant(Expr):
    def __init__(self, tokens: ParseResults, type):
        self.value = tokens.value
        self.type = type


class BinOp(Expr):
    def __init__(self, tokens: ParseResults):
        self.type = TypeUnknow
        self.op = tokens[0][1]
        self.arg1 = tokens[0][0]
        self.arg2 = tokens[0][2]


class IfExpr(Expr):
    def __init__(self, tokens: ParseResults):
        self.type = TypeUnknow
        self.cond = tokens.ifcond
        self.body = tokens.ifbody
        self.elifs = tokens.elifs
        self.elsebody = tokens.eslebody


class FunCall(Expr):
    def __init__(self, tokens: ParseResults):
        self.type = TypeUnknow
        self.name = tokens.name
        self.args = tokens.args

class Statement(Node):
    pass


class Val(Statement):
    def __init__(self, tokens: ParseResults):
        self.name = tokens.name.name
        self.expr = tokens.expr
        self.type = TypeUnknow

    def eval(self):
        self.expr.eval()
        self.type = self.expr.type
        ScopeEnv.push("global", self.name, self.expr)


class FuncDef(Statement):
    def __init__(self, tokens: ParseResults):
        self.name = tokens.name
        self.args = tokens.args
        self.body = tokens.body

    def eval(self):
        print("==========> FunDef statement eval", self);

def eval_statement(self, tokens: ParseResults):
    tokens.stmt[0].eval()


def BNF():
    if hasattr(BNF, "_cache"):
        return BNF._cache

    expr = Forward()

    INT = Word(nums)("value").setParseAction(lambda t: Constant(t, int))
    STRING = dblQuotedString("value").setParseAction(lambda t: Constant(t, str))
    ID = Word(alphas + "_").setParseAction(Identifier)
    BOOL = oneOf("true false")("value").setParseAction(lambda t: Constant(t, bool))

    constant = INT | STRING | BOOL
    value = constant | ID

    mulop = oneOf("* /")
    plusop = oneOf("+ -")

    # fmt: off
    infix_expr = infixNotation(
        value,
        [
            (mulop, 1, opAssoc.LEFT, lambda x: x),
            (plusop, 2, opAssoc.LEFT, BinOp),
        ]

    )
    # fmt: on

    # Expressions
    fun_call = (
        ID("name") + expr("args")[...]
    ).setParseAction(FunCall)

    elif_snippet = "elif" + expr("elifcond") + "then" + expr("elifbody")
    if_expr = (
        "if" + expr("ifcond") + "then" +
            expr("ifbody") +
        elif_snippet("elifs")[...] +
        "else" + expr("elsebody")  +
        "end"
    ).setParseAction(IfExpr)

    expr <<= fun_call ^ value ^ infix_expr ^ if_expr

    expr_list = delimitedList(expr, ";")

    # Statements
    val_stmt = ("val" + ID("name") + "=" + expr("expr") + ";").setParseAction(Val)

    fun_stmt = (
        "fun" + ID("name") + ID("args")[...] + "=" + expr("body") + ";"
    ).setParseAction(FuncDef)


    statement = (val_stmt ^ fun_stmt)("stmt").setParseAction(eval_statement)

    module = statement[1, ...].ignore("#" + restOfLine)

    BNF._cache = module
    return module


BNF().runTests(
    """
    val foo = 10;
    val bar = 20;
    val zar = foo;
    val a = 1 + 2;
    val hello = "Hello";

    fun foofunc a b = a + b;

    val foores = foofunc 1 2;

    val foo = if a then a + 1 elif b then b + 1 else c end;

    val bar = if true then 1 else 0 end;
    """
)
