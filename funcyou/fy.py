import importlib
import ast
import os
import readline as rl
from operator import (add, sub, mul, truediv, lt, le, gt, ge, eq, ne)
import ply.lex as lex
import ply.yacc as yacc

reserved = {
    'from': 'FROM',
    'import': 'IMPORT',
    'as': 'AS'
}

tokens  = (
    'ID', 'NUMBER', 'LPAREN', 'RPAREN',
) + tuple(reserved.values())

t_LPAREN = r'\('
t_RPAREN = r'\)'

def t_NUMBER(t):
    r'(\d+\.)*\d+'
    t.value = float(t.value)
    return t

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*\.?\w*'
    t.type = reserved.get(t.value, 'ID')
    return t

def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

t_ignore = " \t\n"

lex.lex()

precedence = (
    )


def p_statement_expr(p):
    'statement : expression'
    print(p[1])

def p_import_stmt(p):
    'statement : import_stmt'
    print(p[1])

def p_import_stmt_from(p):
    'import_stmt : FROM ID IMPORT ID'
    mod = importlib.import_module(p[2])
    obj = getattr(mod, p[4])
    p[0] = ('import', p[4], obj, mod)

def p_import_stmt_from_as(p):
    'import_stmt : FROM ID IMPORT ID AS ID'
    mod = importlib.import_module(p[2])
    obj = getattr(mod, p[4])
    p[0] = ('import', p[6], obj, mod)

def p_expr_paren(p):
    'par_expression : LPAREN expression RPAREN'
    p[0] = p[2]

def p_expr_paren_expr(p):
    'expression : par_expression'
    p[0] = p[1]

def p_expr_application(p):
    '''expression : partial'''
    p[0] = p[1]

def p_partial(p):
    '''partial : ID arg
               | partial arg'''
    p[0] = (p[1], p[2])

def p_expr_variable(p):
    '''expression : ID
    '''
    p[0] = ('resolve', p[1])

def p_expr_contant(p):
    'expression : NUMBER'
    p[0] = p[1]


def p_arg(p):
    '''arg : ID
           | NUMBER
           | par_expression'''
    p[0] = p[1]

def p_error(p):
    try:
        print("Syntax error at '%s'" % p.value)
    except:
        print("Syntax error")

yacc.yacc()

if __name__ == '__main__':
    while True:
        try:
            s = input('>')
        except EOFError:
            break
        yacc.parse(s + '\n')
