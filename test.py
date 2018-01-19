import farsiscript
import farsiscript.parser

# simple parsing
assert farsiscript.parse('motaghayer i;+9') == {'body': [{'kind': 'motaghayer', 'declarations': [{'init': None, 'type': u'VariableDeclarator', 'id': {'type': u'Identifier', 'name': u'i'}}], 'type': u'VariableDeclaration'}, {'type': u'ExpressionStatement', 'expression': {'operator': u'+', 'prefix': True, 'type': u'UnaryExpression', 'argument': {'raw': None, 'type': u'Literal', 'value': 9.0}}}], 'type': u'Program'}

# errors
try:
    farsiscript.parse('$ = ---')
except farsiscript.JsSyntaxError:
    pass
except:
    raise Exception('Invalid error - should be JsSyntaxError')

farsiscript.parser.ENABLE_JS2PY_ERRORS = True
try:
    farsiscript.parse('$ = ---')
except farsiscript.JsSyntaxError:
    raise Exception('Invalid error - should NOT be JsSyntaxError')
except:
    pass


# pyimport
farsiscript.parser.ENABLE_JS2PY_ERRORS = False
try:
    assert not farsiscript.parse('pyimport abc')
except farsiscript.JsSyntaxError:
    pass

farsiscript.parser.ENABLE_PYIMPORT = True
assert farsiscript.parse('pyimport abc')

