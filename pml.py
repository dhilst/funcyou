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
)
from collections import namedtuple
from collections.abc import MutableMapping
import operator as op

# val foo = 10;

Value = namedtuple("Value", "value type")
Val = namedtuple("Val", "name expr type")
Lookup = namedtuple("Lookup", "name type")
Id = namedtuple("Id", "name type")

# Type will be infered
TypePlaceholder = namedtuple("TypePlaceholder", "id")


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


def push_to_env(v: Val) -> None:
    ScopeEnv.push("global", v.name, v)


def create_val_and_push_to_env(tokens: ParseResults) -> Val:
    val = Val(name=tokens.name, expr=tokens.expr, type=tokens.expr.type)
    push_to_env(val)
    return val


def lookup_val(tokens: ParseResults) -> Lookup:
    val = ScopeEnv.lookup(tokens[0])
    return Lookup(tokens[0], val.type if val is not None else None)


expr = Forward()

INT = Word(nums).setParseAction(lambda tokens: Value(int(tokens[0]), int))
ID = Word(alphas + "_")

val_name = ID.setParseAction(lambda tokens: Id(tokens[0], None))
val_value = ID.setParseAction(lookup_val)

value = INT | val_value

expr <<= value
val_expr = ("val" + val_name("name") + "=" + expr("expr") + ";").setParseAction(
    create_val_and_push_to_env
)
statements = val_expr

module = statements[1, ...].ignore("#" + restOfLine)


##

print(
    module.parseString(
        """
            val foo = 10;
            val bar = 20;
            val zar = foo;
        """,
        True,
    ).dump()
)

print(ScopeEnv.dump())
