from typing import Dict, Any, NamedTuple, Optional, Callable
from pprint import pprint, pformat
from pyparsing import (  # type: ignore
    Combine,
    Forward,
    Group,
    Keyword,
    ParseResults,
    Literal,
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
from collections.abc import MutableMapping
from abc import ABC, abstractmethod, abstractproperty
import operator as op

from pyml.utils import logger, classproperty


class _TypeUnknow:
    def __repr__(self):
        return "any"


TypeUnknow = _TypeUnknow()


class Value:
    def __init__(self, value: Any = None, type=TypeUnknow):
        self.value = value
        self.type: Any = type

    def __repr__(self):
        return f"{self.value}:{self.type.__name__}"


class ScopeEnv:
    """
    Our environment as nested scopes
    """

    # fmt: off
    _scope: Dict[str, Any] = {
        "+": Value(op.add, op.add),
        "-": Value(op.sub, op.sub),
        "%": Value(op.mod, op.mod),
        "*": Value(op.mul, op.mul),
        "/": Value(op.floordiv, op.floordiv),
    }
    # fmt: on

    _current = _scope

    @classmethod
    def push(cls, scope: str, key: str, value: Value):
        "Push value to scope"
        cls._scope.setdefault(scope, {})[key] = value
        cls._current = cls._scope[scope]

    @classmethod
    def pop(cls, scope: str):
        "Pop an scope"
        cls._current = cls._scope

    @classmethod
    def dump(cls) -> str:
        return pformat(cls._scope)

    @classproperty
    def current(cls):
        "Return the current scope"
        return cls._current

    @classproperty
    def current_name(cls):
        for k, v in cls._scope:
            if v is cls._current:
                return k
        return "global"

    @classmethod
    def lookup(cls, key) -> Optional[Any]:
        "Lookup a value from current scope"
        val = cls.current.get(key)
        logger.debug("looking up %s => %s in scope %s", key, val, cls.current)
        if val is not None:
            return val
        val = cls._scope.get(key)
        logger.debug("looking up %s => %s in scope %s", key, val, cls._scope)
        if val is not None:
            return val
        return None


class Node(ABC):
    @abstractmethod
    def __init__(self, tokens: ParseResults):
        self.expr: Optional[Node]
        self.value: Optional[Value]

    def __repr__(self):
        if hasattr(self, "value") and self.value is not None:
            attrs = ", ".join(
                f"{k}={repr(v)}" for k, v in self.__dict__.items() if k != "expr"
            )
        else:
            attrs = ", ".join(
                f"{k}={repr(v)}" for k, v in self.__dict__.items() if k != "value"
            )
        return f"{self.__class__.__name__}({attrs})"


class Identifier(Node):
    def __init__(self, tokens: ParseResults):
        self.name = tokens[0]
        self.value: Optional[Any] = None

    def eval(self):
        if self.value is not None:
            return self.value
        val = ScopeEnv.lookup(self.name)
        logger.debug(
            "Identifier looked up %s => %s:%s", self.name, val.value, val.type.__name__
        )
        self.value = val
        return self.value


class Expr(Node):
    def __init__(self, tokens: ParseResults):
        self.value = Value(tokens.value)

    @abstractmethod
    def eval(self) -> Value:
        pass


class Constant(Expr):
    def __init__(self, tokens: ParseResults, type):
        if type is int:
            v = int(tokens.value)
        elif type is bool:
            v = tokens.value == "true"
        else:
            v = tokens.value
        self.value = Value(v, type)

    def eval(self):
        return self.value


class BinOp(Expr):
    def __init__(self, tokens: ParseResults):
        self.type = TypeUnknow
        self.op = Identifier(tokens[0][1][:])
        self.arg1 = tokens[0][0]
        self.arg2 = tokens[0][2]
        self.value: Optional[Value] = None

    def eval(self) -> Value:
        if self.value is not None:
            return self.value
        logger.debug("evaluate BinOp %s %s %s", self.arg1, self.op, self.arg2)
        self.op.eval()
        self.arg1.eval()
        self.arg2.eval()

        if self.arg1.value.type != self.arg2.value.type:
            raise TypeError("{self.arg1.type} != {self.arg2.type}")
        if self.op.value is None:
            raise LookupError("Can't find {self.op}")

        logger.debug("op => %s", self.op.value.value)
        value = self.op.value.value(self.arg1.value.value, self.arg2.value.value)
        self.value = Value(value, self.arg1.value.type)  # type: ignore
        return self.value


class BoolOp(Expr):
    def eval(self) -> Value:
        return Value(None, bool)


class IfExpr(Expr):
    def __init__(self, tokens: ParseResults):
        self.type = TypeUnknow
        self.cond = tokens.ifcond
        self.body = tokens.ifbody
        self.elsebody = tokens.eslebody

    def eval(self) -> Value:
        return Value(None, None)


class FunCall(Expr):
    def __init__(self, tokens: ParseResults):
        self.type = TypeUnknow
        self.name = tokens.name
        self.args = tokens.args.args

    def eval(self):
        result = ScopeEnv.lookup(self.name).call(self.args)
        self.type = result.type
        return result


class Statement(Node):
    pass


class Val(Statement):
    def __init__(self, tokens: ParseResults):
        self.name = tokens.name.name
        self.value = None
        self.expr: Expr = tokens.expr

    def eval(self):
        if self.value is not None:
            return self.value
        self.expr.eval()
        self.value = self.expr.value
        logger.debug("Val evaluated: %s", self)
        ScopeEnv.push("global", self.name, self.value)


class FuncDef(Statement):
    def __init__(self, tokens: ParseResults):
        self.name = tokens.name.name
        self.args = [t.name for t in tokens.args]
        self.body: Expr = tokens.body

    def eval(self):
        ScopeEnv.push("global", self.name, self)

    def call(self, args):
        self.body.eval(args)


def eval_statement(self, tokens: ParseResults):
    tokens[0].eval()


def BNF():
    if hasattr(BNF, "_cache"):
        return BNF._cache

    expr = Forward()

    INT = Word(nums)("value").setParseAction(lambda t: Constant(t, int))
    STRING = dblQuotedString("value").setParseAction(lambda t: Constant(t, str))
    ID = Word(alphas + "_").setParseAction(Identifier)
    BOOL = oneOf("true false")("value").setParseAction(lambda t: Constant(t, bool))

    IF = Keyword("if")
    THEN = Keyword("then")
    ELSE = Keyword("else")
    END = Keyword("end")
    VAL = Keyword("val")
    FUN = Keyword("fun")

    EQUAL = Literal("=").suppress()
    SEMICOLON = Literal(";").suppress()
    COMMENT = Literal("#").suppress() + restOfLine

    constant = INT | STRING | BOOL
    value = constant | ID

    boolop = oneOf("== != > < >= <=")
    mulop = oneOf("* / %")
    plusop = oneOf("+ -")

    # fmt: off
    infix_expr = infixNotation(
        value,
        [
            (mulop,  2, opAssoc.LEFT, BinOp),
            (plusop, 2, opAssoc.LEFT, BinOp),
            (boolop,  2, opAssoc.LEFT, BoolOp),
        ]

    )
    # fmt: on

    # Expressions
    fun_call_expr = (ID("name") + value("args")).setParseAction(FunCall)

    if_expr = (
        IF + expr("ifcond") + THEN + ELSE + expr("elsebody") + END
    ).setParseAction(IfExpr)

    expr <<= if_expr | infix_expr | fun_call_expr | constant | ID

    expr_list = delimitedList(expr, ";")

    # Statements
    val_stmt = (VAL + ID("name") + EQUAL + expr("expr") + SEMICOLON).setParseAction(Val)

    fun_stmt = (
        FUN + ID("name") + ID[...]("args") + EQUAL + expr("body") + SEMICOLON
    ).setParseAction(FuncDef)

    statement = (val_stmt ^ fun_stmt)("stmt").setParseAction(eval_statement)

    module = statement[1, ...].ignore(COMMENT)

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
    val foofuncres = foofunc 1;
    # fun odd x = x % 2 == 0;
    """
)
