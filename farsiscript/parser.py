# The MIT License
#
# Copyright 2018, 2019 Behrooz Fard
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the 'Software'),
# to deal in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so, subject
# to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
# LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
#  OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
from __future__ import unicode_literals
from .fsparserdata import *
from .std_nodes import *
from pprint import pprint
import sys

__all__ = ['FsParser', 'parse', 'ENABLE_JS2PY_ERRORS', 'ENABLE_PYIMPORT', 'JsSyntaxError']
REGEXP_SPECIAL_SINGLE = ('\\', '^', '$', '*', '+', '?', '.', '[', ']', '(', ')', '{', '{', '|', '-')
ENABLE_PYIMPORT = False
ENABLE_JS2PY_ERRORS = False

PY3 = sys.version_info >= (3, 0)

if PY3:
    basestring = str
    long = int
    xrange = range
    unicode = str

ESPRIMA_VERSION = '2.2.0'
DEBUG = False
# Small naming convention changes
# len -> leng
# id -> d
# type -> typ
# str -> st
true = True
false = False
null = None


def test_reg_exp(pattern, flags):
    # todo: you should return python regexp object
    return pattern, flags


def is_identifier_name(token):
    return token['type'] in (1, 3, 4, 5)


def create_error(line, description):
    global ENABLE_PYIMPORT
    msg = 'Line ' + unicode(line) + ': ' + unicode(description)
    if ENABLE_JS2PY_ERRORS:
        if isinstance(ENABLE_JS2PY_ERRORS, bool):
            import js2py.base
            return js2py.base.MakeError('SyntaxError', msg)
        else:
            return ENABLE_JS2PY_ERRORS(msg)
    else:
        return JsSyntaxError(msg)


def binary_precedence(token, allow_in):
    typ = token['type']
    if typ != Token.Punctuator and typ != Token.Keyword:
        return 0
    val = token['value']
    if val == 'dar' and not allow_in:
        return 0
    return PRECEDENCE.get(val, 0)


class FsParser:
    """ Usage:
        parser = PyJsParser()
        parser.parse('var JavaScriptCode = 5.1')
    """

    def __init__(self):
        self.clean()

    def test(self, code):
        pprint(self.parse(code))

    def clean(self):
        self.strict = None
        self.sourceType = None
        self.index = 0
        self.lineNumber = 1
        self.lineStart = 0
        self.hasLineTerminator = None
        self.lastIndex = None
        self.lastLineNumber = None
        self.lastLineStart = None
        self.startIndex = None
        self.startLineNumber = None
        self.startLineStart = None
        self.scanning = None
        self.lookahead = None
        self.state = None
        self.extra = None
        self.isBindingElement = None
        self.isAssignmentTarget = None
        self.firstCoverInitializedNameError = None

    # 7.4 Comments

    def skip_single_line_comment(self):
        while self.index < self.length:
            ch = self.source[self.index]
            self.index += 1
            if is_line_terminator(ch):
                if ord(ch) == 13 and ord(self.source[self.index]) == 10:
                    self.index += 1
                self.lineNumber += 1
                self.hasLineTerminator = True
                self.lineStart = self.index
                return

    def skip_multi_line_comment(self):
        while self.index < self.length:
            ch = ord(self.source[self.index])
            if is_line_terminator(ch):
                if ch == 0x0D and ord(self.source[self.index + 1]) == 0x0A:
                    self.index += 1
                self.lineNumber += 1
                self.index += 1
                self.hasLineTerminator = True
                self.lineStart = self.index
            elif ch == 0x2A:
                # Block comment ends with '*/'.
                if ord(self.source[self.index + 1]) == 0x2F:
                    self.index += 2
                    return
                self.index += 1
            else:
                self.index += 1
        self.tolerate_unexpected_token()

    def skip_comment(self):
        self.hasLineTerminator = False
        start = (self.index == 0)
        while self.index < self.length:
            ch = ord(self.source[self.index])
            if is_white_space(ch):
                self.index += 1
            elif is_line_terminator(ch):
                self.hasLineTerminator = True
                self.index += 1
                if ch == 0x0D and ord(self.source[self.index]) == 0x0A:
                    self.index += 1
                self.lineNumber += 1
                self.lineStart = self.index
                start = True
            elif ch == 0x2F:  # U+002F is '/'
                ch = ord(self.source[self.index + 1])
                if ch == 0x2F:
                    self.index += 2
                    self.skip_single_line_comment()
                    start = True
                elif ch == 0x2A:  # U+002A is '*'
                    self.index += 2
                    self.skip_multi_line_comment()
                else:
                    break
            elif start and ch == 0x2D:  # U+002D is '-'
                # U+003E is '>'
                if (ord(self.source[self.index + 1]) == 0x2D) and (ord(self.source[self.index + 2]) == 0x3E):
                    # '-->' is a single-line comment
                    self.index += 3
                    self.skip_single_line_comment()
                else:
                    break
            elif ch == 0x3C:  # U+003C is '<'
                if self.source[self.index + 1: self.index + 4] == '!--':
                    # <!--
                    self.index += 4
                    self.skip_single_line_comment()
                else:
                    break
            else:
                break

    def scan_hex_escape(self, prefix):
        code = 0
        length = 4 if (prefix == 'u') else 2
        for i in xrange(length):
            if self.index < self.length and is_hex_digit(self.source[self.index]):
                ch = self.source[self.index]
                self.index += 1
                code = code * 16 + HEX_CONV[ch]
            else:
                return ''
        return unichr(code)

    def scan_unicode_code_point_escape(self):
        ch = self.source[self.index]
        code = 0
        # At least, one hex digit is required.
        if ch == '}':
            self.throw_unexpected_token()
        while self.index < self.length:
            ch = self.source[self.index]
            self.index += 1
            if not is_hex_digit(ch):
                break
            code = code * 16 + HEX_CONV[ch]
        if code > 0x10FFFF or ch != '}':
            self.throw_unexpected_token()
        # UTF-16 Encoding
        if code <= 0xFFFF:
            return unichr(code)
        cu1 = ((code - 0x10000) >> 10) + 0xD800
        cu2 = ((code - 0x10000) & 1023) + 0xDC00
        return unichr(cu1) + unichr(cu2)

    def ccode(self, offset=0):
        return ord(self.source[self.index + offset])

    def log_err_case(self):
        if not DEBUG:
            return
        print('INDEX', self.index)
        print(self.source[self.index - 10:self.index + 10])
        print('')

    def at(self, loc):
        return None if loc >= self.length else self.source[loc]

    def substring(self, le, offset=0):
        return self.source[self.index + offset:self.index + offset + le]

    def get_escaped_identifier(self):
        d = self.source[self.index]
        ch = ord(d)
        self.index += 1
        # '\u' (U+005C, U+0075) denotes an escaped character.
        if ch == 0x5C:
            if ord(self.source[self.index]) != 0x75:
                self.throw_unexpected_token()
            self.index += 1
            ch = self.scan_hex_escape('u')
            if not ch or ch == '\\' or not is_identifier_start(ch[0]):
                self.throw_unexpected_token()
            d = ch
        while self.index < self.length:
            ch = self.ccode()
            if not is_identifier_part(ch):
                break
            self.index += 1
            d += unichr(ch)

            # '\u' (U+005C, U+0075) denotes an escaped character.
            if ch == 0x5C:
                d = d[0: len(d) - 1]
                if self.ccode() != 0x75:
                    self.throw_unexpected_token()
                self.index += 1
                ch = self.scan_hex_escape('u')
                if not ch or ch == '\\' or not is_identifier_part(ch[0]):
                    self.throw_unexpected_token()
                d += ch
        return d

    def get_identifier(self):
        start = self.index
        self.index += 1
        while self.index < self.length:
            ch = self.ccode()
            if ch == 0x5C:
                # Blackslash (U+005C) marks Unicode escape sequence.
                self.index = start
                return self.get_escaped_identifier()
            if is_identifier_part(ch):
                self.index += 1
            else:
                break
        return self.source[start: self.index]

    def scan_identifier(self):
        start = self.index

        # Backslash (U+005C) starts an escaped character.
        d = self.get_escaped_identifier() if (self.ccode() == 0x5C) else self.get_identifier()

        # There is no keyword or literal with only one character.
        # Thus, it must be an identifier.
        if len(d) == 1:
            type = Token.Identifier
        elif is_keyword(d):
            type = Token.Keyword
        elif d == 'null':
            type = Token.NullLiteral
        elif d == 'true' or d == 'false':
            type = Token.BooleanLiteral
        else:
            type = Token.Identifier
        return {
            'type': type,
            'value': d,
            'lineNumber': self.lineNumber,
            'lineStart': self.lineStart,
            'start': start,
            'end': self.index
        }

    # 7.7 Punctuators

    def scan_punctuator(self):
        token = {
            'type': Token.Punctuator,
            'value': '',
            'lineNumber': self.lineNumber,
            'lineStart': self.lineStart,
            'start': self.index,
            'end': self.index
        }
        # Check for most common single-character punctuators.
        st = self.source[self.index]
        if st == '{':
            self.state['curlyStack'].append('{')
            self.index += 1
        elif st == '}':
            self.index += 1
            self.state['curlyStack'].pop()
        elif st in ('.', '(', ')', ';', ',', '[', ']', ':', '?', '~'):
            self.index += 1
        else:
            # 4-character punctuator.
            st = self.substring(4)
            if st == '>>>=':
                self.index += 4
            else:
                # 3-character punctuators.
                st = st[0:3]
                if st in ('===', '!==', '>>>', '<<=', '>>='):
                    self.index += 3
                else:
                    # 2-character punctuators.
                    st = st[0:2]
                    if st in ('&&', '||', '==', '!=', '+=', '-=', '*=', '/=', '++', '--', '<<', '>>', '&=', '|=', '^=',
                              '%=', '<=', '>=', '=>'):
                        self.index += 2
                    else:
                        # 1-character punctuators.
                        st = self.source[self.index]
                        if st in ('<', '>', '=', '!', '+', '-', '*', '%', '&', '|', '^', '/'):
                            self.index += 1
        if self.index == token['start']:
            self.throw_unexpected_token()
        token['end'] = self.index
        token['value'] = st
        return token

    # 7.8.3 Numeric Literals

    def scan_hex_literal(self, start):
        number = ''
        while self.index < self.length:
            if not is_hex_digit(self.source[self.index]):
                break
            number += self.source[self.index]
            self.index += 1
        if not number:
            self.throw_unexpected_token()
        if is_identifier_start(self.ccode()):
            self.throw_unexpected_token()
        return {
            'type': Token.NumericLiteral,
            'value': int(number, 16),
            'lineNumber': self.lineNumber,
            'lineStart': self.lineStart,
            'start': start,
            'end': self.index}

    def scan_binary_literal(self, start):
        number = ''
        while self.index < self.length:
            ch = self.source[self.index]
            if ch != '0' and ch != '1':
                break
            number += self.source[self.index]
            self.index += 1

        if not number:
            # only 0b or 0B
            self.throw_unexpected_token()
        if self.index < self.length:
            ch = self.source[self.index]
            # istanbul ignore else
            if is_identifier_start(ch) or is_decimal_digit(ch):
                self.throw_unexpected_token()
        return {
            'type': Token.NumericLiteral,
            'value': int(number, 2),
            'lineNumber': self.lineNumber,
            'lineStart': self.lineStart,
            'start': start,
            'end': self.index}

    def scan_octal_literal(self, prefix, start):
        if is_octal_digit(prefix):
            octal = True
            number = '0' + self.source[self.index]
            self.index += 1
        else:
            octal = False
            self.index += 1
            number = ''
        while self.index < self.length:
            if not is_octal_digit(self.source[self.index]):
                break
            number += self.source[self.index]
            self.index += 1
        if not octal and not number:
            # only 0o or 0O
            self.throw_unexpected_token()
        if is_identifier_start(self.ccode()) or is_decimal_digit(self.ccode()):
            self.throw_unexpected_token()
        return {
            'type': Token.NumericLiteral,
            'value': int(number, 8),
            'lineNumber': self.lineNumber,
            'lineStart': self.lineStart,
            'start': start,
            'end': self.index}

    def octal_to_decimal(self, ch):
        # \0 is not octal escape sequence
        octal = (ch != '0')
        code = int(ch, 8)

        if self.index < self.length and is_octal_digit(self.source[self.index]):
            octal = True
            code = code * 8 + int(self.source[self.index], 8)
            self.index += 1

            # 3 digits are only allowed when string starts
            # with 0, 1, 2, 3
            if ch in '0123' and self.index < self.length and is_octal_digit(self.source[self.index]):
                code = code * 8 + int((self.source[self.index]), 8)
                self.index += 1
        return {
            'code': code,
            'octal': octal}

    def is_implicit_octal_literal(self):
        # Implicit octal, unless there is a non-octal digit.
        # (Annex B.1.1 on Numeric Literals)
        for i in xrange(self.index + 1, self.length):
            ch = self.source[i]
            if ch == '8' or ch == '9':
                return False
            if not is_octal_digit(ch):
                return True
        return True

    def scan_numeric_literal(self):
        ch = self.source[self.index]
        assert is_decimal_digit(ch) or (ch == '.'), 'Numeric literal must start with a decimal digit or a decimal point'
        start = self.index
        number = ''
        if ch != '.':
            number = self.source[self.index]
            self.index += 1
            ch = self.source[self.index]
            # Hex number starts with '0x'.
            # Octal number starts with '0'.
            # Octal number in ES6 starts with '0o'.
            # Binary number in ES6 starts with '0b'.
            if number == '0':
                if ch == 'x' or ch == 'X':
                    self.index += 1
                    return self.scan_hex_literal(start)
                if ch == 'b' or ch == 'B':
                    self.index += 1
                    return self.scan_binary_literal(start)
                if ch == 'o' or ch == 'O':
                    return self.scan_octal_literal(ch, start)
                if is_octal_digit(ch):
                    if self.is_implicit_octal_literal():
                        return self.scan_octal_literal(ch, start)
            while is_decimal_digit(self.ccode()):
                number += self.source[self.index]
                self.index += 1
            ch = self.source[self.index]
        if ch == '.':
            number += self.source[self.index]
            self.index += 1
            while is_decimal_digit(self.source[self.index]):
                number += self.source[self.index]
                self.index += 1
            ch = self.source[self.index]
        if ch == 'e' or ch == 'E':
            number += self.source[self.index]
            self.index += 1
            ch = self.source[self.index]
            if ch == '+' or ch == '-':
                number += self.source[self.index]
                self.index += 1
            if is_decimal_digit(self.source[self.index]):
                while is_decimal_digit(self.source[self.index]):
                    number += self.source[self.index]
                    self.index += 1
            else:
                self.throw_unexpected_token()
        if is_identifier_start(self.source[self.index]):
            self.throw_unexpected_token()
        return {
            'type': Token.NumericLiteral,
            'value': float(number),
            'lineNumber': self.lineNumber,
            'lineStart': self.lineStart,
            'start': start,
            'end': self.index}

    # 7.8.4 String Literals

    def _interpret_regexp(self, string):
        """Perform string escape - for regexp literals"""
        self.index = 0
        self.length = len(string)
        self.source = string
        self.lineNumber = 0
        self.lineStart = 0
        st = ''
        inside_square = 0
        while self.index < self.length:
            template = '[%s]' if not inside_square else '%s'
            ch = self.source[self.index]
            self.index += 1
            if ch == '\\':
                ch = self.source[self.index]
                self.index += 1
                if not is_line_terminator(ch):
                    if ch == 'u':
                        digs = self.source[self.index:self.index + 4]
                        if len(digs) == 4 and all(is_hex_digit(d) for d in digs):
                            st += template % unichr(int(digs, 16))
                            self.index += 4
                        else:
                            st += 'u'
                    elif ch == 'x':
                        digs = self.source[self.index:self.index + 2]
                        if len(digs) == 2 and all(is_hex_digit(d) for d in digs):
                            st += template % unichr(int(digs, 16))
                            self.index += 2
                        else:
                            st += 'x'
                    # special meaning - single char.
                    elif ch == '0':
                        st += '\\0'
                    elif ch == 'n':
                        st += '\\n'
                    elif ch == 'r':
                        st += '\\r'
                    elif ch == 't':
                        st += '\\t'
                    elif ch == 'f':
                        st += '\\f'
                    elif ch == 'v':
                        st += '\\v'

                    # unescape special single characters like . so that they are interpreted literally
                    elif ch in REGEXP_SPECIAL_SINGLE:
                        st += '\\' + ch

                    # character groups
                    elif ch == 'b':
                        st += '\\b'
                    elif ch == 'B':
                        st += '\\B'
                    elif ch == 'w':
                        st += '\\w'
                    elif ch == 'W':
                        st += '\\W'
                    elif ch == 'd':
                        st += '\\d'
                    elif ch == 'D':
                        st += '\\D'
                    elif ch == 's':
                        st += template % u'\f\n\r\t\v\u00a0\u1680\u180e\u2000-\u200a\u2028\u2029\u202f\u205f\u3000' \
                                         u'\ufeff '
                    elif ch == 'S':
                        st += template % u'\u0000-\u0008\u000e-\u001f\u0021-\u009f\u00a1-\u167f\u1681-\u180d\u180f' \
                                         u'-\u1fff\u200b-\u2027\u202a-\u202e\u2030-\u205e\u2060-\u2fff\u3001-\ufefe' \
                                         u'\uff00-\uffff '
                    else:
                        if is_decimal_digit(ch):
                            num = ch
                            while self.index < self.length and is_decimal_digit(self.source[self.index]):
                                num += self.source[self.index]
                                self.index += 1
                            st += '\\' + num

                        else:
                            st += ch  # DONT ESCAPE!!!
                else:
                    self.lineNumber += 1
                    if ch == '\r' and self.source[self.index] == '\n':
                        self.index += 1
                    self.lineStart = self.index
            else:
                if ch == '[':
                    inside_square = True
                elif ch == ']':
                    inside_square = False
                st += ch
        # print string, 'was transformed to', st
        return st

    def scan_string_literal(self):
        st = ''
        octal = False

        quote = self.source[self.index]
        assert quote == '\'' or quote == '"', 'String literal must starts with a quote'
        start = self.index
        self.index += 1

        while self.index < self.length:
            ch = self.source[self.index]
            self.index += 1
            if ch == quote:
                quote = ''
                break
            elif ch == '\\':
                ch = self.source[self.index]
                self.index += 1
                if not is_line_terminator(ch):
                    if ch in 'ux':
                        if self.source[self.index] == '{':
                            self.index += 1
                            st += self.scan_unicode_code_point_escape()
                        else:
                            unescaped = self.scan_hex_escape(ch)
                            if not unescaped:
                                self.throw_unexpected_token()  # with throw I don't know whats the difference
                            st += unescaped
                    elif ch == 'n':
                        st += '\n'
                    elif ch == 'r':
                        st += '\r'
                    elif ch == 't':
                        st += '\t'
                    elif ch == 'b':
                        st += '\b'
                    elif ch == 'f':
                        st += '\f'
                    elif ch == 'v':
                        st += '\x0B'
                    # elif ch in '89':
                    #    self.throw_unexpected_token() # again with throw....
                    else:
                        if is_octal_digit(ch):
                            octToDec = self.octal_to_decimal(ch)
                            octal = octToDec.get('octal') or octal
                            st += unichr(octToDec['code'])
                        else:
                            st += ch
                else:
                    self.lineNumber += 1
                    if ch == '\r' and self.source[self.index] == '\n':
                        self.index += 1
                    self.lineStart = self.index
            elif is_line_terminator(ch):
                break
            else:
                st += ch
        if quote != '':
            self.throw_unexpected_token()
        return {
            'type': Token.StringLiteral,
            'value': st,
            'octal': octal,
            'lineNumber': self.lineNumber,
            'lineStart': self.startLineStart,
            'start': start,
            'end': self.index}

    def scan_template(self):
        cooked = ''
        terminated = False
        tail = False
        start = self.index
        head = (self.source[self.index] == '`')
        rawOffset = 2

        self.index += 1

        while self.index < self.length:
            ch = self.source[self.index]
            self.index += 1
            if ch == '`':
                rawOffset = 1
                tail = True
                terminated = True
                break
            elif ch == '$':
                if self.source[self.index] == '{':
                    self.state['curlyStack'].append('${')
                    self.index += 1
                    terminated = True
                    break
                cooked += ch
            elif ch == '\\':
                ch = self.source[self.index]
                self.index += 1
                if not is_line_terminator(ch):
                    if ch == 'n':
                        cooked += '\n'
                    elif ch == 'r':
                        cooked += '\r'
                    elif ch == 't':
                        cooked += '\t'
                    elif ch in 'ux':
                        if self.source[self.index] == '{':
                            self.index += 1
                            cooked += self.scan_unicode_code_point_escape()
                        else:
                            restore = self.index
                            unescaped = self.scan_hex_escape(ch)
                            if unescaped:
                                cooked += unescaped
                            else:
                                self.index = restore
                                cooked += ch
                    elif ch == 'b':
                        cooked += '\b'
                    elif ch == 'f':
                        cooked += '\f'
                    elif ch == 'v':
                        cooked += '\v'
                    else:
                        if ch == '0':
                            if is_decimal_digit(self.ccode()):
                                # Illegal: \01 \02 and so on
                                self.throw_error(Messages.TemplateOctalLiteral)
                            cooked += '\0'
                        elif is_octal_digit(ch):
                            # Illegal: \1 \2
                            self.throw_error(Messages.TemplateOctalLiteral)
                        else:
                            cooked += ch
                else:
                    self.lineNumber += 1
                    if ch == '\r' and self.source[self.index] == '\n':
                        self.index += 1
                    self.lineStart = self.index
            elif is_line_terminator(ch):
                self.lineNumber += 1
                if ch == '\r' and self.source[self.index] == '\n':
                    self.index += 1
                self.lineStart = self.index
                cooked += '\n'
            else:
                cooked += ch
        if not terminated:
            self.throw_unexpected_token()

        if not head:
            self.state['curlyStack'].pop()

        return {
            'type': Token.Template,
            'value': {
                'cooked': cooked,
                'raw': self.source[start + 1:self.index - rawOffset]},
            'head': head,
            'tail': tail,
            'lineNumber': self.lineNumber,
            'lineStart': self.lineStart,
            'start': start,
            'end': self.index}

    def scan_reg_exp_body(self):
        ch = self.source[self.index]
        assert ch == '/', 'Regular expression literal must start with a slash'
        st = ch
        self.index += 1

        classMarker = False
        terminated = False
        while self.index < self.length:
            ch = self.source[self.index]
            self.index += 1
            st += ch
            if ch == '\\':
                ch = self.source[self.index]
                self.index += 1
                # ECMA-262 7.8.5
                if is_line_terminator(ch):
                    self.throw_unexpected_token(None, Messages.UnterminatedRegExp)
                st += ch
            elif is_line_terminator(ch):
                self.throw_unexpected_token(None, Messages.UnterminatedRegExp)
            elif classMarker:
                if ch == ']':
                    classMarker = False
            else:
                if ch == '/':
                    terminated = True
                    break
                elif ch == '[':
                    classMarker = True
        if not terminated:
            self.throw_unexpected_token(None, Messages.UnterminatedRegExp)

        # Exclude leading and trailing slash.
        body = st[1:-1]
        return {
            'value': body,
            'literal': st}

    def scan_reg_exp_flags(self):
        st = ''
        flags = ''
        while self.index < self.length:
            ch = self.source[self.index]
            if not is_identifier_part(ch):
                break
            self.index += 1
            if ch == '\\' and self.index < self.length:
                ch = self.source[self.index]
                if ch == 'u':
                    self.index += 1
                    restore = self.index
                    ch = self.scan_hex_escape('u')
                    if ch:
                        flags += ch
                        st += '\\u'
                        while restore < self.index:
                            st += self.source[restore]
                            restore += 1
                    else:
                        self.index = restore
                        flags += 'u'
                        st += '\\u'
                    self.tolerate_unexpected_token()
                else:
                    st += '\\'
                    self.tolerate_unexpected_token()
            else:
                flags += ch
                st += ch
        return {
            'value': flags,
            'literal': st}

    def scan_reg_exp(self):
        self.scanning = True
        self.lookahead = None
        self.skip_comment()
        start = self.index

        body = self.scan_reg_exp_body()
        flags = self.scan_reg_exp_flags()
        value = test_reg_exp(body['value'], flags['value'])
        return {
            'literal': body['literal'] + flags['literal'],
            'value': value,
            'regex': {
                'pattern': body['value'],
                'flags': flags['value']
            },
            'start': start,
            'end': self.index}

    def collect_regex(self):
        self.skip_comment()
        return self.scan_reg_exp()

    # def advanceSlash(self): ???

    def advance(self):
        if self.index >= self.length:
            return {
                'type': Token.EOF,
                'lineNumber': self.lineNumber,
                'lineStart': self.lineStart,
                'start': self.index,
                'end': self.index}
        ch = self.ccode()

        if is_identifier_start(ch):
            token = self.scan_identifier()
            if self.strict and is_strict_mode_reserved_word(token['value']):
                token['type'] = Token.Keyword
            return token
        # Very common: ( and ) and ;
        if ch == 0x28 or ch == 0x29 or ch == 0x3B:
            return self.scan_punctuator()

        # String literal starts with single quote (U+0027) or double quote (U+0022).
        if ch == 0x27 or ch == 0x22:
            return self.scan_string_literal()

        # Dot (.) U+002E can also start a floating-point number, hence the need
        # to check the next character.
        if ch == 0x2E:
            if is_decimal_digit(self.ccode(1)):
                return self.scan_numeric_literal()
            return self.scan_punctuator()

        if is_decimal_digit(ch):
            return self.scan_numeric_literal()

        # Slash (/) U+002F can also start a regex.
        # if (extra.tokenize && ch == 0x2F):
        #    return advanceSlash();

        # Template literals start with ` (U+0060) for template head
        # or } (U+007D) for template middle or template tail.
        if ch == 0x60 or (ch == 0x7D and self.state['curlyStack'][len(self.state['curlyStack']) - 1] == '${'):
            return self.scan_template()
        return self.scan_punctuator()

    def lex(self):
        self.scanning = True

        self.lastIndex = self.index
        self.lastLineNumber = self.lineNumber
        self.lastLineStart = self.lineStart

        self.skip_comment()

        token = self.lookahead

        self.startIndex = self.index
        self.startLineNumber = self.lineNumber
        self.startLineStart = self.lineStart

        self.lookahead = self.advance()
        self.scanning = False
        return token

    def peek(self):
        self.scanning = True

        self.skip_comment()

        self.lastIndex = self.index
        self.lastLineNumber = self.lineNumber
        self.lastLineStart = self.lineStart

        self.startIndex = self.index
        self.startLineNumber = self.lineNumber
        self.startLineStart = self.lineStart

        self.lookahead = self.advance()
        self.scanning = False

    # Throw an exception
    def throw_error(self, message_format, *args):
        msg = message_format % tuple(unicode(e) for e in args)
        raise create_error(self.lastLineNumber, msg)

    def tolerate_error(self, message_format, *args):
        return self.throw_error(message_format, *args)

    # Throw an exception because of the token.

    def unexpected_token_error(self, token=None, message=''):
        if token is None:
            token = {}
        msg = message or Messages.UnexpectedToken
        if token:
            typ = token['type']
            if not message:
                if typ == Token.EOF:
                    msg = Messages.UnexpectedEOS
                elif typ == Token.Identifier:
                    msg = Messages.UnexpectedIdentifier
                elif typ == Token.NumericLiteral:
                    msg = Messages.UnexpectedNumber
                elif typ == Token.StringLiteral:
                    msg = Messages.UnexpectedString
                elif typ == Token.Template:
                    msg = Messages.UnexpectedTemplate
                else:
                    msg = Messages.UnexpectedToken
                if typ == Token.Keyword:
                    if is_future_reserved_word(token['value']):
                        msg = Messages.UnexpectedReserved
                    elif self.strict and is_strict_mode_reserved_word(token['value']):
                        msg = Messages.StrictReservedWord
            value = token['value']['raw'] if (typ == Token.Template) else token.get('value')
        else:
            value = 'ILLEGAL'
        msg = msg.replace('%s', unicode(value))

        return (create_error(token['lineNumber'], msg) if (token and token.get('lineNumber')) else
                create_error(self.lineNumber if self.scanning else self.lastLineNumber,
                             msg))

    def throw_unexpected_token(self, token=None, message=''):
        if token is None:
            token = {}
        raise self.unexpected_token_error(token, message)

    def tolerate_unexpected_token(self, token=None, message=''):
        if token is None:
            token = {}
        self.throw_unexpected_token(token, message)

    # Expect the next token to match the specified punctuator.
    # If not, an exception will be thrown.

    def expect(self, value):
        token = self.lex()
        if token['type'] != Token.Punctuator or token['value'] != value:
            self.throw_unexpected_token(token)

    # /**
    # * @name expect_comma_separator
    # * @description Quietly expect a comma when in tolerant mode, otherwise delegates
    # * to <code>expect(value)</code>
    # * @since 2.0
    # */
    def expect_comma_separator(self):
        self.expect(',')

    # Expect the next token to match the specified keyword.
    # If not, an exception will be thrown.

    def expect_keyword(self, keyword):
        token = self.lex()
        if token['type'] != Token.Keyword or token['value'] != keyword:
            self.throw_unexpected_token(token)

    # Return true if the next token matches the specified punctuator.

    def match(self, value):
        return self.lookahead['type'] == Token.Punctuator and self.lookahead['value'] == value

    # Return true if the next token matches the specified keyword

    def match_keyword(self, keyword):
        return self.lookahead['type'] == Token.Keyword and self.lookahead['value'] == keyword

    # Return true if the next token matches the specified contextual keyword
    # (where an identifier is sometimes a keyword depending on the context)

    def match_contextual_keyword(self, keyword):
        return self.lookahead['type'] == Token.Identifier and self.lookahead['value'] == keyword

    # Return true if the next token is an assignment operator

    def match_assign(self):
        if self.lookahead['type'] != Token.Punctuator:
            return False
        op = self.lookahead['value']
        return op in ('=', '*=', '/=', '%=', '+=', '-=', '<<=', '>>=', '>>>=', '&=', '^=', '|=')

    def consume_semicolon(self):
        # Catch the very common case first: immediately a semicolon (U+003B).
        if self.at(self.startIndex) == ';' or self.match(';'):
            self.lex()
            return

        if self.hasLineTerminator:
            return

        self.lastIndex = self.startIndex
        self.lastLineNumber = self.startLineNumber
        self.lastLineStart = self.startLineStart

        if self.lookahead['type'] != Token.EOF and not self.match('}'):
            self.throw_unexpected_token(self.lookahead)

    # // Cover grammar support. // // When an assignment expression position starts with an left parenthesis,
    # the determination of the type // of the syntax is to be deferred arbitrarily long until the end of the
    # parentheses pair (plus a lookahead) // or the first comma. This situation also defers the determination of all
    # the expressions nested in the pair. // // There are three productions that can be parsed in a parentheses pair
    # that needs to be determined // after the outermost pair is closed. They are: // //   1. AssignmentExpression //
    #    2. BindingElements //   3. AssignmentTargets // // In order to avoid exponential backtracking, we use two
    # flags to denote if the production can be // binding element or assignment target. // // The three productions
    # have the relationship: // //   BindingElements <= AssignmentTargets <= AssignmentExpression // // with a single
    #  exception that CoverInitializedName when used directly in an Expression, generates // an early error.
    # Therefore, we need the third state, firstCoverInitializedNameError, to track the // first usage of
    # CoverInitializedName and report it when we reached the end of the parentheses pair. // // isolate_cover_grammar
    #  function runs the given parser function with a new cover grammar context, and it does not // effect the
    # current flags. This means the production the parser parses is only used as an expression. Therefore // the
    # CoverInitializedName check is conducted. // // inherit_cover_grammar function runs the given parse function
    # with a new cover grammar context, and it propagates // the flags outside of the parser. This means the
    # production the parser parses is used as a part of a potential // pattern. The CoverInitializedName check is
    # deferred.

    def isolate_cover_grammar(self, parser):
        oldIsBindingElement = self.isBindingElement
        oldIsAssignmentTarget = self.isAssignmentTarget
        oldFirstCoverInitializedNameError = self.firstCoverInitializedNameError
        self.isBindingElement = true
        self.isAssignmentTarget = true
        self.firstCoverInitializedNameError = null
        result = parser()
        if self.firstCoverInitializedNameError != null:
            self.throw_unexpected_token(self.firstCoverInitializedNameError)
        self.isBindingElement = oldIsBindingElement
        self.isAssignmentTarget = oldIsAssignmentTarget
        self.firstCoverInitializedNameError = oldFirstCoverInitializedNameError
        return result

    def inherit_cover_grammar(self, parser):
        oldIsBindingElement = self.isBindingElement
        oldIsAssignmentTarget = self.isAssignmentTarget
        oldFirstCoverInitializedNameError = self.firstCoverInitializedNameError
        self.isBindingElement = true
        self.isAssignmentTarget = true
        self.firstCoverInitializedNameError = null
        result = parser()
        self.isBindingElement = self.isBindingElement and oldIsBindingElement
        self.isAssignmentTarget = self.isAssignmentTarget and oldIsAssignmentTarget
        self.firstCoverInitializedNameError = oldFirstCoverInitializedNameError or self.firstCoverInitializedNameError
        return result

    def parse_array_pattern(self):
        node = Node()
        elements = []
        self.expect('[')
        while not self.match(']'):
            if self.match(','):
                self.lex()
                elements.append(null)
            else:
                if self.match('...'):
                    restNode = Node()
                    self.lex()
                    rest = self.parse_variable_identifier()
                    elements.append(restNode.finishRestElement(rest))
                    break
                else:
                    elements.append(self.parse_pattern_with_default())
                if not self.match(']'):
                    self.expect(',')
        self.expect(']')
        return node.finish_array_pattern(elements)

    def parse_property_pattern(self):
        node = Node()
        computed = self.match('[')
        if self.lookahead['type'] == Token.Identifier:
            key = self.parse_variable_identifier()
            if self.match('='):
                self.lex()
                init = self.parse_assignment_expression()
                return node.finishProperty(
                    'init', key, false, WrappingNode().finish_assignment_pattern(key, init), false, false)
            elif not self.match(':'):
                return node.finishProperty('init', key, false, key, false, true)
        else:
            key = self.parse_object_property_key()
        self.expect(':')
        init = self.parse_pattern_with_default()
        return node.finishProperty('init', key, computed, init, false, false)

    def parse_object_pattern(self):
        node = Node()
        properties = []
        self.expect('{')
        while not self.match('}'):
            properties.append(self.parse_property_pattern())
            if not self.match('}'):
                self.expect(',')
        self.lex()
        return node.finishObjectPattern(properties)

    def parse_pattern(self):
        if self.lookahead['type'] == Token.Identifier:
            return self.parse_variable_identifier()
        elif self.match('['):
            return self.parse_array_pattern()
        elif self.match('{'):
            return self.parse_object_pattern()
        self.throw_unexpected_token(self.lookahead)

    def parse_pattern_with_default(self):

        pattern = self.parse_pattern()
        if self.match('='):
            self.lex()
            right = self.isolate_cover_grammar(self.parse_assignment_expression)
            pattern = WrappingNode().finish_assignment_pattern(pattern, right)
        return pattern

    # 11.1.4 Array Initialiser

    def parse_array_initialiser(self):
        elements = []
        node = Node()

        self.expect('[')

        while not self.match(']'):
            if self.match(','):
                self.lex()
                elements.append(null)
            elif self.match('...'):
                restSpread = Node()
                self.lex()
                restSpread.finishSpreadElement(self.inherit_cover_grammar(self.parse_assignment_expression))
                if not self.match(']'):
                    self.isAssignmentTarget = self.isBindingElement = false
                    self.expect(',')
                elements.append(restSpread)
            else:
                elements.append(self.inherit_cover_grammar(self.parse_assignment_expression))
                if not self.match(']'):
                    self.expect(',')
        self.lex()

        return node.finish_array_expression(elements)

    # 11.1.5 Object Initialiser

    def parse_property_function(self, node, param_info):

        self.isAssignmentTarget = self.isBindingElement = false

        previousStrict = self.strict
        body = self.isolate_cover_grammar(self.parse_function_source_elements)

        if self.strict and param_info['firstRestricted']:
            self.tolerate_unexpected_token(param_info['firstRestricted'], param_info.get('message'))
        if self.strict and param_info.get('stricted'):
            self.tolerate_unexpected_token(param_info.get('stricted'), param_info.get('message'))

        self.strict = previousStrict
        return node.finish_function_expression(null, param_info.get('params'), param_info.get('defaults'), body)

    def parse_property_method_function(self):
        node = Node()

        params = self.parse_params(null)
        method = self.parse_property_function(node, params)
        return method

    def parse_object_property_key(self):
        node = Node()

        token = self.lex()

        # // Note: This function is called only from parse_object_property(), where
        # // EOF and Punctuator tokens are already filtered out.

        typ = token['type']

        if typ in [Token.StringLiteral, Token.NumericLiteral]:
            if self.strict and token.get('octal'):
                self.tolerate_unexpected_token(token, Messages.StrictOctalLiteral)
            return node.finishLiteral(token)
        elif typ in (Token.Identifier, Token.BooleanLiteral, Token.NullLiteral, Token.Keyword):
            return node.finish_identifier(token['value'])
        elif typ == Token.Punctuator:
            if token['value'] == '[':
                expr = self.isolate_cover_grammar(self.parse_assignment_expression)
                self.expect(']')
                return expr
        self.throw_unexpected_token(token)

    def lookahead_property_name(self):
        typ = self.lookahead['type']
        if typ in (Token.Identifier, Token.StringLiteral, Token.BooleanLiteral, Token.NullLiteral, Token.NumericLiteral,
                   Token.Keyword):
            return true
        if typ == Token.Punctuator:
            return self.lookahead['value'] == '['
        return false

    # // This function is to try to parse a MethodDefinition as defined in 14.3. But in the case of object literals,
    # // it might be called at a position where there is in fact a short hand identifier pattern or a data property.
    # // This can only be determined after we consumed up to the left parentheses.
    # //
    # // In order to avoid back tracking, it returns `null` if the position is not a MethodDefinition and the caller
    # // is responsible to visit other options.
    def try_parse_method_definition(self, token, key, computed, node):
        if token['type'] == Token.Identifier:
            # check for `get` and `set`;

            if token['value'] == 'get' and self.lookahead_property_name():
                computed = self.match('[')
                key = self.parse_object_property_key()
                methodNode = Node()
                self.expect('(')
                self.expect(')')
                value = self.parse_property_function(methodNode, {
                    'params': [],
                    'defaults': [],
                    'stricted': null,
                    'firstRestricted': null,
                    'message': null
                })
                return node.finishProperty('get', key, computed, value, false, false)
            elif token['value'] == 'set' and self.lookahead_property_name():
                computed = self.match('[')
                key = self.parse_object_property_key()
                methodNode = Node()
                self.expect('(')

                options = {
                    'params': [],
                    'defaultCount': 0,
                    'defaults': [],
                    'firstRestricted': null,
                    'paramSet': {}
                }
                if self.match(')'):
                    self.tolerate_unexpected_token(self.lookahead)
                else:
                    self.parse_param(options)
                    if options['defaultCount'] == 0:
                        options['defaults'] = []
                self.expect(')')

                value = self.parse_property_function(methodNode, options)
                return node.finishProperty('set', key, computed, value, false, false)
        if self.match('('):
            value = self.parse_property_method_function()
            return node.finishProperty('init', key, computed, value, true, false)
        return null

    def check_proto(self, key, computed, has_proto):
        if (computed == false and (key['type'] == Syntax.Identifier and key['name'] == '__proto__' or
                                   key['type'] == Syntax.Literal and key['value'] == '__proto__')):
            if has_proto['value']:
                self.tolerate_error(Messages.DuplicateProtoProperty)
            else:
                has_proto['value'] = true

    def parse_object_property(self, has_proto):
        token = self.lookahead
        node = Node()

        computed = self.match('[')
        key = self.parse_object_property_key()
        maybeMethod = self.try_parse_method_definition(token, key, computed, node)

        if maybeMethod:
            self.check_proto(maybeMethod['key'], maybeMethod['computed'], has_proto)
            return maybeMethod

        # // init property or short hand property.
        self.check_proto(key, computed, has_proto)

        if self.match(':'):
            self.lex()
            value = self.inherit_cover_grammar(self.parse_assignment_expression)
            return node.finishProperty('init', key, computed, value, false, false)

        if token['type'] == Token.Identifier:
            if self.match('='):
                self.firstCoverInitializedNameError = self.lookahead
                self.lex()
                value = self.isolate_cover_grammar(self.parse_assignment_expression)
                return node.finishProperty('init', key, computed,
                                           WrappingNode().finish_assignment_pattern(key, value), false, true)
            return node.finishProperty('init', key, computed, key, false, true)
        self.throw_unexpected_token(self.lookahead)

    def parse_object_initialiser(self):
        properties = []
        hasProto = {'value': false}
        node = Node()

        self.expect('{')

        while not self.match('}'):
            properties.append(self.parse_object_property(hasProto))

            if not self.match('}'):
                self.expect_comma_separator()
        self.expect('}')
        return node.finishObjectExpression(properties)

    def reinterpret_expression_as_pattern(self, expr):
        typ = (expr['type'])
        if typ in (Syntax.Identifier, Syntax.MemberExpression, Syntax.RestElement, Syntax.AssignmentPattern):
            pass
        elif typ == Syntax.SpreadElement:
            expr['type'] = Syntax.RestElement
            self.reinterpret_expression_as_pattern(expr.argument)
        elif typ == Syntax.ArrayExpression:
            expr['type'] = Syntax.ArrayPattern
            for i in xrange(len(expr['elements'])):
                if expr['elements'][i] != null:
                    self.reinterpret_expression_as_pattern(expr['elements'][i])
        elif typ == Syntax.ObjectExpression:
            expr['type'] = Syntax.ObjectPattern
            for i in xrange(len(expr['properties'])):
                self.reinterpret_expression_as_pattern(expr['properties'][i]['value'])
        elif Syntax.AssignmentExpression:
            expr['type'] = Syntax.AssignmentPattern
            self.reinterpret_expression_as_pattern(expr['left'])
        else:
            # // Allow other node type for tolerant parsing.
            return

    def parse_template_element(self, option):

        if self.lookahead['type'] != Token.Template or (option['head'] and not self.lookahead['head']):
            self.throw_unexpected_token()

        node = Node()
        token = self.lex()

        return node.finishTemplateElement({'raw': token['value']['raw'], 'cooked': token['value']['cooked']},
                                          token['tail'])

    def parse_template_literal(self):
        node = Node()

        quasi = self.parse_template_element({'head': true})
        quasis = [quasi]
        expressions = []

        while not quasi['tail']:
            expressions.append(self.parse_expression())
            quasi = self.parse_template_element({'head': false})
            quasis.append(quasi)
        return node.finishTemplateLiteral(quasis, expressions)

    # 11.1.6 The Grouping Operator

    def parse_group_expression(self):
        self.expect('(')

        if self.match(')'):
            self.lex()
            if not self.match('=>'):
                self.expect('=>')
            return {
                'type': PlaceHolders.ArrowParameterPlaceHolder,
                'params': []}

        if self.match('...'):
            expr = self.parse_rest_element()
            self.expect(')')
            if not self.match('=>'):
                self.expect('=>')
            return {
                'type': PlaceHolders.ArrowParameterPlaceHolder,
                'params': [expr]}

        self.isBindingElement = true
        expr = self.inherit_cover_grammar(self.parse_assignment_expression)

        if self.match(','):
            self.isAssignmentTarget = false
            expressions = [expr]

            while self.startIndex < self.length:
                if not self.match(','):
                    break
                self.lex()

                if self.match('...'):
                    if not self.isBindingElement:
                        self.throw_unexpected_token(self.lookahead)
                    expressions.append(self.parse_rest_element())
                    self.expect(')')
                    if not self.match('=>'):
                        self.expect('=>')
                    self.isBindingElement = false
                    for i in xrange(len(expressions)):
                        self.reinterpret_expression_as_pattern(expressions[i])
                    return {
                        'type': PlaceHolders.ArrowParameterPlaceHolder,
                        'params': expressions}
                expressions.append(self.inherit_cover_grammar(self.parse_assignment_expression))
            expr = WrappingNode().finishSequenceExpression(expressions)
        self.expect(')')

        if self.match('=>'):
            if not self.isBindingElement:
                self.throw_unexpected_token(self.lookahead)
            if expr['type'] == Syntax.SequenceExpression:
                for i in xrange(len(expr.expressions)):
                    self.reinterpret_expression_as_pattern(expr['expressions'][i])
            else:
                self.reinterpret_expression_as_pattern(expr)
            expr = {
                'type': PlaceHolders.ArrowParameterPlaceHolder,
                'params': expr['expressions'] if expr['type'] == Syntax.SequenceExpression else [expr]}
        self.isBindingElement = false
        return expr

    # 11.1 Primary Expressions

    def parse_primary_expression(self):
        if self.match('('):
            self.isBindingElement = false
            return self.inherit_cover_grammar(self.parse_group_expression)
        if self.match('['):
            return self.inherit_cover_grammar(self.parse_array_initialiser)

        if self.match('{'):
            return self.inherit_cover_grammar(self.parse_object_initialiser)

        typ = self.lookahead['type']
        node = Node()

        if typ == Token.Identifier:
            expr = node.finish_identifier(self.lex()['value'])
        elif typ == Token.StringLiteral or typ == Token.NumericLiteral:
            self.isAssignmentTarget = self.isBindingElement = false
            if self.strict and self.lookahead.get('octal'):
                self.tolerate_unexpected_token(self.lookahead, Messages.StrictOctalLiteral)
            expr = node.finishLiteral(self.lex())
        elif typ == Token.Keyword:
            self.isAssignmentTarget = self.isBindingElement = false
            if self.match_keyword('tabe'):
                return self.parse_function_expression()
            if self.match_keyword('this'):
                self.lex()
                return node.finishThisExpression()
            if self.match_keyword('class'):
                return self.parse_class_expression()
            self.throw_unexpected_token(self.lex())
        elif typ == Token.BooleanLiteral:
            token = self.lex()
            token['value'] = (token['value'] == 'true')
            expr = node.finishLiteral(token)
        elif typ == Token.NullLiteral:
            self.isAssignmentTarget = self.isBindingElement = false
            token = self.lex()
            token['value'] = null
            expr = node.finishLiteral(token)
        elif self.match('/') or self.match('/='):
            self.isAssignmentTarget = self.isBindingElement = false
            self.index = self.startIndex
            token = self.scan_reg_exp()
            self.lex()
            expr = node.finishLiteral(token)
        elif typ == Token.Template:
            expr = self.parse_template_literal()
        else:
            self.throw_unexpected_token(self.lex())
        return expr

    # 11.2 Left-Hand-Side Expressions

    def parseArguments(self):
        args = []

        self.expect('(')
        if not self.match(')'):
            while self.startIndex < self.length:
                args.append(self.isolate_cover_grammar(self.parse_assignment_expression))
                if self.match(')'):
                    break
                self.expect_comma_separator()
        self.expect(')')
        return args

    def parse_non_computed_property(self):
        node = Node()

        token = self.lex()

        if not is_identifier_name(token):
            self.throw_unexpected_token(token)
        return node.finish_identifier(token['value'])

    def parse_con_computed_member(self):
        self.expect('.')
        return self.parse_non_computed_property()

    def parse_computed_member(self):
        self.expect('[')

        expr = self.isolate_cover_grammar(self.parse_expression)
        self.expect(']')

        return expr

    def parse_new_expression(self):
        node = Node()
        self.expect_keyword('jadid')
        callee = self.isolate_cover_grammar(self.parse_left_hand_side_expression)
        args = self.parseArguments() if self.match('(') else []

        self.isAssignmentTarget = self.isBindingElement = false

        return node.finishNewExpression(callee, args)

    def parse_left_hand_side_expression_allow_call(self):
        previousAllowIn = self.state['allowIn']

        self.state['allowIn'] = true

        if self.match_keyword('super') and self.state['inFunctionBody']:
            expr = Node()
            self.lex()
            expr = expr.finishSuper()
            if not self.match('(') and not self.match('.') and not self.match('['):
                self.throw_unexpected_token(self.lookahead)
        else:
            expr = self.inherit_cover_grammar(
                self.parse_new_expression if self.match_keyword('jadid') else self.parse_primary_expression)
        while True:
            if self.match('.'):
                self.isBindingElement = false
                self.isAssignmentTarget = true
                property = self.parse_con_computed_member()
                expr = WrappingNode().finishMemberExpression('.', expr, property)
            elif self.match('('):
                self.isBindingElement = false
                self.isAssignmentTarget = false
                args = self.parseArguments()
                expr = WrappingNode().finish_call_expression(expr, args)
            elif self.match('['):
                self.isBindingElement = false
                self.isAssignmentTarget = true
                property = self.parse_computed_member()
                expr = WrappingNode().finishMemberExpression('[', expr, property)
            elif self.lookahead['type'] == Token.Template and self.lookahead['head']:
                quasi = self.parse_template_literal()
                expr = WrappingNode().finishTaggedTemplateExpression(expr, quasi)
            else:
                break
        self.state['allowIn'] = previousAllowIn

        return expr

    def parse_left_hand_side_expression(self):
        assert self.state['allowIn'], 'callee of new expression always allow in keyword.'

        if self.match_keyword('super') and self.state['inFunctionBody']:
            expr = Node()
            self.lex()
            expr = expr.finishSuper()
            if not self.match('[') and not self.match('.'):
                self.throw_unexpected_token(self.lookahead)
        else:
            expr = self.inherit_cover_grammar(
                self.parse_new_expression if self.match_keyword('jadid') else self.parse_primary_expression)

        while True:
            if self.match('['):
                self.isBindingElement = false
                self.isAssignmentTarget = true
                property = self.parse_computed_member()
                expr = WrappingNode().finishMemberExpression('[', expr, property)
            elif self.match('.'):
                self.isBindingElement = false
                self.isAssignmentTarget = true
                property = self.parse_con_computed_member()
                expr = WrappingNode().finishMemberExpression('.', expr, property)
            elif self.lookahead['type'] == Token.Template and self.lookahead['head']:
                quasi = self.parse_template_literal()
                expr = WrappingNode().finishTaggedTemplateExpression(expr, quasi)
            else:
                break
        return expr

    # 11.3 Postfix Expressions

    def parse_postfix_expression(self):

        expr = self.inherit_cover_grammar(self.parse_left_hand_side_expression_allow_call)

        if not self.hasLineTerminator and self.lookahead['type'] == Token.Punctuator:
            if self.match('++') or self.match('--'):
                # 11.3.1, 11.3.2
                if self.strict and expr.type == Syntax.Identifier and is_restricted_word(expr.name):
                    self.tolerate_error(Messages.StrictLHSPostfix)
                if not self.isAssignmentTarget:
                    self.tolerate_error(Messages.InvalidLHSInAssignment)
                self.isAssignmentTarget = self.isBindingElement = false

                token = self.lex()
                expr = WrappingNode().finishPostfixExpression(token['value'], expr)
        return expr

    # 11.4 Unary Operators

    def parse_unary_expression(self):

        if self.lookahead['type'] != Token.Punctuator and self.lookahead['type'] != Token.Keyword:
            expr = self.parse_postfix_expression()
        elif self.match('++') or self.match('--'):
            token = self.lex()
            expr = self.inherit_cover_grammar(self.parse_unary_expression)
            # 11.4.4, 11.4.5
            if self.strict and expr.type == Syntax.Identifier and is_restricted_word(expr.name):
                self.tolerate_error(Messages.StrictLHSPrefix)
            if not self.isAssignmentTarget:
                self.tolerate_error(Messages.InvalidLHSInAssignment)
            expr = WrappingNode().finishUnaryExpression(token['value'], expr)
            self.isAssignmentTarget = self.isBindingElement = false
        elif self.match('+') or self.match('-') or self.match('~') or self.match('!'):
            token = self.lex()
            expr = self.inherit_cover_grammar(self.parse_unary_expression)
            expr = WrappingNode().finishUnaryExpression(token['value'], expr)
            self.isAssignmentTarget = self.isBindingElement = false
        elif self.match_keyword('delete') or self.match_keyword('void') or self.match_keyword('typeof'):
            token = self.lex()
            expr = self.inherit_cover_grammar(self.parse_unary_expression)
            expr = WrappingNode().finishUnaryExpression(token['value'], expr)
            if self.strict and expr.operator == 'delete' and expr.argument.type == Syntax.Identifier:
                self.tolerate_error(Messages.StrictDelete)
            self.isAssignmentTarget = self.isBindingElement = false
        else:
            expr = self.parse_postfix_expression()
        return expr

    # 11.5 Multiplicative Operators
    # 11.6 Additive Operators
    # 11.7 Bitwise Shift Operators
    # 11.8 Relational Operators
    # 11.9 Equality Operators
    # 11.10 Binary Bitwise Operators
    # 11.11 Binary Logical Operators

    def parse_binary_expression(self):

        marker = self.lookahead
        left = self.inherit_cover_grammar(self.parse_unary_expression)

        token = self.lookahead
        prec = binary_precedence(token, self.state['allowIn'])
        if prec == 0:
            return left
        self.isAssignmentTarget = self.isBindingElement = false
        token['prec'] = prec
        self.lex()

        markers = [marker, self.lookahead]
        right = self.isolate_cover_grammar(self.parse_unary_expression)

        stack = [left, token, right]

        while True:
            prec = binary_precedence(self.lookahead, self.state['allowIn'])
            if not prec > 0:
                break
            # Reduce: make a binary expression from the three topmost entries.
            while (len(stack) > 2) and (prec <= stack[len(stack) - 2]['prec']):
                right = stack.pop()
                operator = stack.pop()['value']
                left = stack.pop()
                markers.pop()
                expr = WrappingNode().finish_binary_expression(operator, left, right)
                stack.append(expr)

            # Shift
            token = self.lex()
            token['prec'] = prec
            stack.append(token)
            markers.append(self.lookahead)
            expr = self.isolate_cover_grammar(self.parse_unary_expression)
            stack.append(expr)

        # Final reduce to clean-up the stack.
        i = len(stack) - 1
        expr = stack[i]
        markers.pop()
        while i > 1:
            expr = WrappingNode().finish_binary_expression(stack[i - 1]['value'], stack[i - 2], expr)
            i -= 2
        return expr

    # 11.12 Conditional Operator

    def parse_conditional_expression(self):

        expr = self.inherit_cover_grammar(self.parse_binary_expression)
        if self.match('?'):
            self.lex()
            previousAllowIn = self.state['allowIn']
            self.state['allowIn'] = true
            consequent = self.isolate_cover_grammar(self.parse_assignment_expression)
            self.state['allowIn'] = previousAllowIn
            self.expect(':')
            alternate = self.isolate_cover_grammar(self.parse_assignment_expression)

            expr = WrappingNode().finish_conditional_expression(expr, consequent, alternate)
            self.isAssignmentTarget = self.isBindingElement = false
        return expr

    # [ES6] 14.2 Arrow Function

    def parse_concise_body(self):
        if self.match('{'):
            return self.parse_function_source_elements()
        return self.isolate_cover_grammar(self.parse_assignment_expression)

    def check_pattern_param(self, options, param):
        typ = param.type
        if typ == Syntax.Identifier:
            self.validate_param(options, param, param.name)
        elif typ == Syntax.RestElement:
            self.check_pattern_param(options, param.argument)
        elif typ == Syntax.AssignmentPattern:
            self.check_pattern_param(options, param.left)
        elif typ == Syntax.ArrayPattern:
            for i in xrange(len(param.elements)):
                if param.elements[i] != null:
                    self.check_pattern_param(options, param.elements[i])
        else:
            assert typ == Syntax.ObjectPattern, 'Invalid type'
            for i in xrange(len(param.properties)):
                self.check_pattern_param(options, param.properties[i]['value'])

    def reinterpret_as_cover_formals_list(self, expr):
        defaults = []
        defaultCount = 0
        params = [expr]
        typ = expr.type
        if typ == Syntax.Identifier:
            pass
        elif typ == PlaceHolders.ArrowParameterPlaceHolder:
            params = expr.params
        else:
            return null
        options = {
            'paramSet': {}}
        le = len(params)
        for i in xrange(le):
            param = params[i]
            if param.type == Syntax.AssignmentPattern:
                params[i] = param.left
                defaults.append(param.right)
                defaultCount += 1
                self.check_pattern_param(options, param.left)
            else:
                self.check_pattern_param(options, param)
                params[i] = param
                defaults.append(null)
        if options.get('message') == Messages.StrictParamDupe:
            token = options.get('stricted') if self.strict else options['firstRestricted']
            self.throw_unexpected_token(token, options.get('message'))
        if defaultCount == 0:
            defaults = []
        return {
            'params': params,
            'defaults': defaults,
            'stricted': options['stricted'],
            'firstRestricted': options['firstRestricted'],
            'message': options.get('message')}

    def parse_arrow_function_expression(self, options, node):
        if self.hasLineTerminator:
            self.tolerate_unexpected_token(self.lookahead)
        self.expect('=>')
        previousStrict = self.strict

        body = self.parse_concise_body()

        if self.strict and options['firstRestricted']:
            self.throw_unexpected_token(options['firstRestricted'], options.get('message'))
        if self.strict and options['stricted']:
            self.tolerate_unexpected_token(options['stricted'], options['message'])

        self.strict = previousStrict

        return node.finish_arrow_function_expression(options['params'], options['defaults'], body,
                                                     body.type != Syntax.BlockStatement)

    # 11.13 Assignment Operators

    def parse_assignment_expression(self):
        token = self.lookahead

        expr = self.parse_conditional_expression()

        if expr.type == PlaceHolders.ArrowParameterPlaceHolder or self.match('=>'):
            self.isAssignmentTarget = self.isBindingElement = false
            lis = self.reinterpret_as_cover_formals_list(expr)

            if lis:
                self.firstCoverInitializedNameError = null
                return self.parse_arrow_function_expression(lis, WrappingNode())
            return expr

        if self.match_assign():
            if not self.isAssignmentTarget or expr.type == Syntax.Literal:
                self.tolerate_error(Messages.InvalidLHSInAssignment)
            # 11.13.1

            if self.strict and expr.type == Syntax.Identifier and is_restricted_word(expr.name):
                self.tolerate_unexpected_token(token, Messages.StrictLHSAssignment)
            if not self.match('='):
                self.isAssignmentTarget = self.isBindingElement = false
            else:
                self.reinterpret_expression_as_pattern(expr)
            token = self.lex()
            right = self.isolate_cover_grammar(self.parse_assignment_expression)
            expr = WrappingNode().finish_assignment_expression(token['value'], expr, right)
            self.firstCoverInitializedNameError = null
        return expr

    # 11.14 Comma Operator

    def parse_expression(self):
        expr = self.isolate_cover_grammar(self.parse_assignment_expression)

        if self.match(','):
            expressions = [expr]

            while self.startIndex < self.length:
                if not self.match(','):
                    break
                self.lex()
                expressions.append(self.isolate_cover_grammar(self.parse_assignment_expression))
            expr = WrappingNode().finishSequenceExpression(expressions)
        return expr

    # 12.1 Block

    def parse_statement_listItem(self):
        if self.lookahead['type'] == Token.Keyword:
            val = (self.lookahead['value'])
            if val == 'export':
                if self.sourceType != 'module':
                    self.tolerate_unexpected_token(self.lookahead, Messages.IllegalExportDeclaration)
                return self.parseExportDeclaration()
            elif val == 'import':
                if self.sourceType != 'module':
                    self.tolerate_unexpected_token(self.lookahead, Messages.IllegalImportDeclaration)
                return self.parseImportDeclaration()
            elif val == 'const' or val == 'let':
                return self.parse_lexical_declaration({'inFor': false})
            elif val == 'tabe':
                return self.parse_function_declaration(Node())
            elif val == 'class':
                return self.parse_class_declaration()
            elif ENABLE_PYIMPORT and val == 'pyimport':  # <<<<< MODIFIED HERE
                return self.parse_pyimport_statement()
        return self.parse_statement()

    def parse_pyimport_statement(self):
        print(ENABLE_PYIMPORT)
        assert ENABLE_PYIMPORT
        n = Node()
        self.lex()
        n.finishPyimport(self.parse_variable_identifier())
        self.consume_semicolon()
        return n

    def parse_statement_list(self):
        list = []
        while self.startIndex < self.length:
            if self.match('}'):
                break
            list.append(self.parse_statement_listItem())
        return list

    def parse_block(self):
        node = Node()

        self.expect('{')

        block = self.parse_statement_list()

        self.expect('}')

        return node.finish_block_statement(block)

    # 12.2 Variable Statement

    def parse_variable_identifier(self):
        node = Node()

        token = self.lex()

        if token['type'] != Token.Identifier:
            if self.strict and token['type'] == Token.Keyword and is_strict_mode_reserved_word(token['value']):
                self.tolerate_unexpected_token(token, Messages.StrictReservedWord)
            else:
                self.throw_unexpected_token(token)
        return node.finish_identifier(token['value'])

    def parse_variable_declaration(self):
        init = null
        node = Node()

        d = self.parse_pattern()

        # 12.2.1
        if self.strict and is_restricted_word(d.name):
            self.tolerate_error(Messages.StrictVarName)

        if self.match('='):
            self.lex()
            init = self.isolate_cover_grammar(self.parse_assignment_expression)
        elif d.type != Syntax.Identifier:
            self.expect('=')
        return node.finishVariableDeclarator(d, init)

    def parse_variable_declaration_list(self):
        lis = []

        while True:
            lis.append(self.parse_variable_declaration())
            if not self.match(','):
                break
            self.lex()
            if not (self.startIndex < self.length):
                break

        return lis

    def parse_variable_statement(self, node):
        self.expect_keyword('motaghayer')

        declarations = self.parse_variable_declaration_list()

        self.consume_semicolon()

        return node.finishVariableDeclaration(declarations)

    def parse_lexical_binding(self, kind, options):
        init = null
        node = Node()

        d = self.parse_pattern()

        # 12.2.1
        if self.strict and d.type == Syntax.Identifier and is_restricted_word(d.name):
            self.tolerate_error(Messages.StrictVarName)

        if kind == 'const':
            if not self.match_keyword('dar'):
                self.expect('=')
                init = self.isolate_cover_grammar(self.parse_assignment_expression)
        elif (not options['inFor'] and d.type != Syntax.Identifier) or self.match('='):
            self.expect('=')
            init = self.isolate_cover_grammar(self.parse_assignment_expression)
        return node.finishVariableDeclarator(d, init)

    def parse_binding_list(self, kind, options):
        list = []

        while True:
            list.append(self.parse_lexical_binding(kind, options))
            if not self.match(','):
                break
            self.lex()
            if not (self.startIndex < self.length):
                break
        return list

    def parse_lexical_declaration(self, options):
        node = Node()

        kind = self.lex()['value']
        assert kind == 'let' or kind == 'const', 'Lexical declaration must be either let or const'
        declarations = self.parse_binding_list(kind, options)
        self.consume_semicolon()
        return node.finishLexicalDeclaration(declarations, kind)

    def parse_rest_element(self):
        node = Node()

        self.lex()

        if self.match('{'):
            self.throw_error(Messages.ObjectPatternAsRestParameter)
        param = self.parse_variable_identifier()
        if self.match('='):
            self.throw_error(Messages.DefaultRestParameter)

        if not self.match(')'):
            self.throw_error(Messages.ParameterAfterRestParameter)
        return node.finishRestElement(param)

    # 12.3 Empty Statement

    def parse_empty_statement(self, node):
        self.expect(';')
        return node.finish_empty_statement()

    # 12.4 Expression Statement

    def parse_expression_statement(self, node):
        expr = self.parse_expression()
        self.consume_semicolon()
        return node.finish_expression_statement(expr)

    # 12.5 If statement

    def parse_if_statement(self, node):
        self.expect_keyword('agar')

        self.expect('(')

        test = self.parse_expression()

        self.expect(')')

        consequent = self.parse_statement()

        if self.match_keyword('varna'):
            self.lex()
            alternate = self.parse_statement()
        else:
            alternate = null
        return node.finish_if_statement(test, consequent, alternate)

    # 12.6 Iteration Statements

    def parse_do_while_statement(self, node):

        self.expect_keyword('anjambede')

        oldInIteration = self.state['inIteration']
        self.state['inIteration'] = true

        body = self.parse_statement()

        self.state['inIteration'] = oldInIteration

        self.expect_keyword('tavaghti')

        self.expect('(')

        test = self.parse_expression()

        self.expect(')')

        if self.match(';'):
            self.lex()
        return node.finish_do_while_statement(body, test)

    def parse_while_statement(self, node):

        self.expect_keyword('tavaghti')

        self.expect('(')

        test = self.parse_expression()

        self.expect(')')

        oldInIteration = self.state['inIteration']
        self.state['inIteration'] = true

        body = self.parse_statement()

        self.state['inIteration'] = oldInIteration

        return node.finishWhileStatement(test, body)

    def parse_for_statement(self, node):
        previousAllowIn = self.state['allowIn']

        init = test = update = null

        self.expect_keyword('baraye')

        self.expect('(')

        if self.match(';'):
            self.lex()
        else:
            if self.match_keyword('motaghayer'):
                init = Node()
                self.lex()

                self.state['allowIn'] = false
                init = init.finishVariableDeclaration(self.parse_variable_declaration_list())
                self.state['allowIn'] = previousAllowIn

                if len(init.declarations) == 1 and self.match_keyword('dar'):
                    self.lex()
                    left = init
                    right = self.parse_expression()
                    init = null
                else:
                    self.expect(';')
            elif self.match_keyword('const') or self.match_keyword('let'):
                init = Node()
                kind = self.lex()['value']

                self.state['allowIn'] = false
                declarations = self.parse_binding_list(kind, {'inFor': true})
                self.state['allowIn'] = previousAllowIn

                if len(declarations) == 1 and declarations[0].init == null and self.match_keyword('dar'):
                    init = init.finishLexicalDeclaration(declarations, kind)
                    self.lex()
                    left = init
                    right = self.parse_expression()
                    init = null
                else:
                    self.consume_semicolon()
                    init = init.finishLexicalDeclaration(declarations, kind)
            else:
                initStartToken = self.lookahead
                self.state['allowIn'] = false
                init = self.inherit_cover_grammar(self.parse_assignment_expression)
                self.state['allowIn'] = previousAllowIn

                if self.match_keyword('dar'):
                    if not self.isAssignmentTarget:
                        self.tolerate_error(Messages.InvalidLHSInForIn)
                    self.lex()
                    self.reinterpret_expression_as_pattern(init)
                    left = init
                    right = self.parse_expression()
                    init = null
                else:
                    if self.match(','):
                        initSeq = [init]
                        while self.match(','):
                            self.lex()
                            initSeq.append(self.isolate_cover_grammar(self.parse_assignment_expression))
                        init = WrappingNode().finishSequenceExpression(initSeq)
                    self.expect(';')

        if 'left' not in locals():
            if not self.match(';'):
                test = self.parse_expression()

            self.expect(';')

            if not self.match(')'):
                update = self.parse_expression()

        self.expect(')')

        oldInIteration = self.state['inIteration']
        self.state['inIteration'] = true

        body = self.isolate_cover_grammar(self.parse_statement)

        self.state['inIteration'] = oldInIteration

        return node.finish_for_statement(init, test, update, body) if (
                'left' not in locals()) else node.finish_for_in_statement(left, right, body)

    # 12.7 The continue statement

    def parse_continue_statement(self, node):
        label = null

        self.expect_keyword('edame')

        # Optimize the most common form: 'continue;'.
        if ord(self.source[self.startIndex]) == 0x3B:
            self.lex()
            if not self.state['inIteration']:
                self.throw_error(Messages.IllegalContinue)
            return node.finish_continue_statement(null)
        if self.hasLineTerminator:
            if not self.state['inIteration']:
                self.throw_error(Messages.IllegalContinue)
            return node.finish_continue_statement(null)

        if self.lookahead['type'] == Token.Identifier:
            label = self.parse_variable_identifier()

            key = '$' + label.name
            if key not in self.state['labelSet']:  # todo make sure its correct!
                self.throw_error(Messages.UnknownLabel, label.name)
        self.consume_semicolon()

        if label == null and not self.state['inIteration']:
            self.throw_error(Messages.IllegalContinue)
        return node.finish_continue_statement(label)

    # 12.8 The break statement

    def parse_break_statement(self, node):
        label = null

        self.expect_keyword('bebor')

        # Catch the very common case first: immediately a semicolon (U+003B).
        if ord(self.source[self.lastIndex]) == 0x3B:
            self.lex()
            if not (self.state['inIteration'] or self.state['inSwitch']):
                self.throw_error(Messages.IllegalBreak)
            return node.finish_break_statement(null)
        if self.hasLineTerminator:
            if not (self.state['inIteration'] or self.state['inSwitch']):
                self.throw_error(Messages.IllegalBreak)
            return node.finish_break_statement(null)
        if self.lookahead['type'] == Token.Identifier:
            label = self.parse_variable_identifier()

            key = '$' + label.name
            if not (key in self.state['labelSet']):
                self.throw_error(Messages.UnknownLabel, label.name)
        self.consume_semicolon()

        if label == null and not (self.state['inIteration'] or self.state['inSwitch']):
            self.throw_error(Messages.IllegalBreak)
        return node.finish_break_statement(label)

    # 12.9 The return statement

    def parse_return_statement(self, node):
        argument = null

        self.expect_keyword('bazgardan')

        if not self.state['inFunctionBody']:
            self.tolerate_error(Messages.IllegalReturn)

        # 'return' followed by a space and an identifier is very common.
        if ord(self.source[self.lastIndex]) == 0x20:
            if is_identifier_start(self.source[self.lastIndex + 1]):
                argument = self.parse_expression()
                self.consume_semicolon()
                return node.finishReturnStatement(argument)
        if self.hasLineTerminator:
            # HACK
            return node.finishReturnStatement(null)

        if not self.match(';'):
            if not self.match('}') and self.lookahead['type'] != Token.EOF:
                argument = self.parse_expression()
        self.consume_semicolon()

        return node.finishReturnStatement(argument)

    # 12.10 The with statement

    def parse_with_statement(self, node):
        if self.strict:
            self.tolerate_error(Messages.StrictModeWith)

        self.expect_keyword('with')

        self.expect('(')

        obj = self.parse_expression()

        self.expect(')')

        body = self.parse_statement()

        return node.finishWithStatement(obj, body)

    # 12.10 The swith statement

    def parse_switch_case(self):
        consequent = []
        node = Node()

        if self.match_keyword('pishfarz'):
            self.lex()
            test = null
        else:
            self.expect_keyword('mored')
            test = self.parse_expression()

        self.expect(':')

        while self.startIndex < self.length:
            if self.match('}') or self.match_keyword('pishfarz') or self.match_keyword('mored'):
                break
            statement = self.parse_statement_listItem()
            consequent.append(statement)
        return node.finishSwitchCase(test, consequent)

    def parse_switch_statement(self, node):

        self.expect_keyword('bargozin')

        self.expect('(')

        discriminant = self.parse_expression()

        self.expect(')')

        self.expect('{')

        cases = []

        if self.match('}'):
            self.lex()
            return node.finishSwitchStatement(discriminant, cases)

        oldInSwitch = self.state['inSwitch']
        self.state['inSwitch'] = true
        defaultFound = false

        while self.startIndex < self.length:
            if self.match('}'):
                break
            clause = self.parse_switch_case()
            if clause.test == null:
                if defaultFound:
                    self.throw_error(Messages.MultipleDefaultsInSwitch)
                defaultFound = true
            cases.append(clause)

        self.state['inSwitch'] = oldInSwitch

        self.expect('}')

        return node.finishSwitchStatement(discriminant, cases)

    # 12.13 The throw statement

    def parse_throw_statement(self, node):

        self.expect_keyword('partkon')

        if self.hasLineTerminator:
            self.throw_error(Messages.NewlineAfterThrow)

        argument = self.parse_expression()

        self.consume_semicolon()

        return node.finishThrowStatement(argument)

    # 12.14 The try statement

    def parse_catch_clause(self):
        node = Node()

        self.expect_keyword('begir')

        self.expect('(')
        if self.match(')'):
            self.throw_unexpected_token(self.lookahead)
        param = self.parse_pattern()

        # 12.14.1
        if self.strict and is_restricted_word(param.name):
            self.tolerate_error(Messages.StrictCatchVariable)

        self.expect(')')
        body = self.parse_block()
        return node.finish_catch_clause(param, body)

    def parse_try_statement(self, node):
        handler = null
        finalizer = null

        self.expect_keyword('bekoosh')

        block = self.parse_block()

        if self.match_keyword('begir'):
            handler = self.parse_catch_clause()

        if self.match_keyword('darnahayat'):
            self.lex()
            finalizer = self.parse_block()

        if not handler and not finalizer:
            self.throw_error(Messages.NoCatchOrFinally)

        return node.finishTryStatement(block, handler, finalizer)

    # 12.15 The debugger statement

    def parse_debugger_statement(self, node):
        self.expect_keyword('eshkalzodaee')

        self.consume_semicolon()

        return node.finish_debugger_statement()

    # 12 Statements

    def parse_statement(self):
        typ = self.lookahead['type']

        if typ == Token.EOF:
            self.throw_unexpected_token(self.lookahead)

        if typ == Token.Punctuator and self.lookahead['value'] == '{':
            return self.parse_block()

        self.isAssignmentTarget = self.isBindingElement = true
        node = Node()
        val = self.lookahead['value']

        if typ == Token.Punctuator:
            if val == ';':
                return self.parse_empty_statement(node)
            elif val == '(':
                return self.parse_expression_statement(node)
        elif typ == Token.Keyword:
            if val == 'bebor':
                return self.parse_break_statement(node)
            elif val == 'edame':
                return self.parse_continue_statement(node)
            elif val == 'eshkalzodaee':
                return self.parse_debugger_statement(node)
            elif val == 'anjambede':
                return self.parse_do_while_statement(node)
            elif val == 'baraye':
                return self.parse_for_statement(node)
            elif val == 'tabe':
                return self.parse_function_declaration(node)
            elif val == 'agar':
                return self.parse_if_statement(node)
            elif val == 'bazgardan':
                return self.parse_return_statement(node)
            elif val == 'bargozin':
                return self.parse_switch_statement(node)
            elif val == 'partkon':
                return self.parse_throw_statement(node)
            elif val == 'bekoosh':
                return self.parse_try_statement(node)
            elif val == 'motaghayer':
                return self.parse_variable_statement(node)
            elif val == 'tavaghti':
                return self.parse_while_statement(node)
            elif val == 'with':
                return self.parse_with_statement(node)

        expr = self.parse_expression()

        # 12.12 Labelled Statements
        if (expr.type == Syntax.Identifier) and self.match(':'):
            self.lex()

            key = '$' + expr.name
            if key in self.state['labelSet']:
                self.throw_error(Messages.Redeclaration, 'Label', expr.name)
            self.state['labelSet'][key] = true
            labeledBody = self.parse_statement()
            del self.state['labelSet'][key]
            return node.finishLabeledStatement(expr, labeledBody)
        self.consume_semicolon()
        return node.finish_expression_statement(expr)

    # 13 Function Definition

    def parse_function_source_elements(self):
        body = []
        node = Node()
        firstRestricted = None

        self.expect('{')

        while self.startIndex < self.length:
            if self.lookahead['type'] != Token.StringLiteral:
                break
            token = self.lookahead

            statement = self.parse_statement_listItem()
            body.append(statement)
            if statement.expression.type != Syntax.Literal:
                # this is not directive
                break
            directive = self.source[token['start'] + 1: token['end'] - 1]
            if directive == 'use strict':
                self.strict = true
                if firstRestricted:
                    self.tolerate_unexpected_token(firstRestricted, Messages.StrictOctalLiteral)
            else:
                if not firstRestricted and token.get('octal'):
                    firstRestricted = token

        oldLabelSet = self.state['labelSet']
        oldInIteration = self.state['inIteration']
        oldInSwitch = self.state['inSwitch']
        oldInFunctionBody = self.state['inFunctionBody']
        oldParenthesisCount = self.state['parenthesizedCount']

        self.state['labelSet'] = {}
        self.state['inIteration'] = false
        self.state['inSwitch'] = false
        self.state['inFunctionBody'] = true
        self.state['parenthesizedCount'] = 0

        while self.startIndex < self.length:
            if self.match('}'):
                break
            body.append(self.parse_statement_listItem())
        self.expect('}')

        self.state['labelSet'] = oldLabelSet
        self.state['inIteration'] = oldInIteration
        self.state['inSwitch'] = oldInSwitch
        self.state['inFunctionBody'] = oldInFunctionBody
        self.state['parenthesizedCount'] = oldParenthesisCount

        return node.finish_block_statement(body)

    def validate_param(self, options, param, name):
        key = '$' + name
        if self.strict:
            if is_restricted_word(name):
                options['stricted'] = param
                options['message'] = Messages.StrictParamName
            if key in options['paramSet']:
                options['stricted'] = param
                options['message'] = Messages.StrictParamDupe
        elif not options['firstRestricted']:
            if is_restricted_word(name):
                options['firstRestricted'] = param
                options['message'] = Messages.StrictParamName
            elif is_strict_mode_reserved_word(name):
                options['firstRestricted'] = param
                options['message'] = Messages.StrictReservedWord
            elif key in options['paramSet']:
                options['firstRestricted'] = param
                options['message'] = Messages.StrictParamDupe
        options['paramSet'][key] = true

    def parse_param(self, options):
        token = self.lookahead
        de = None
        if token['value'] == '...':
            param = self.parse_rest_element()
            self.validate_param(options, param.argument, param.argument.name)
            options['params'].append(param)
            options['defaults'].append(null)
            return false
        param = self.parse_pattern_with_default()
        self.validate_param(options, token, token['value'])

        if param.type == Syntax.AssignmentPattern:
            de = param.right
            param = param.left
            options['defaultCount'] += 1
        options['params'].append(param)
        options['defaults'].append(de)
        return not self.match(')')

    def parse_params(self, first_restricted):
        options = {
            'params': [],
            'defaultCount': 0,
            'defaults': [],
            'first_restricted': first_restricted}

        self.expect('(')

        if not self.match(')'):
            options['paramSet'] = {}
            while self.startIndex < self.length:
                if not self.parse_param(options):
                    break
                self.expect(',')
        self.expect(')')

        if options['defaultCount'] == 0:
            options['defaults'] = []

        return {
            'params': options['params'],
            'defaults': options['defaults'],
            'stricted': options.get('stricted'),
            'first_restricted': options.get('first_restricted'),
            'message': options.get('message')}

    def parse_function_declaration(self, node, identifier_is_optional=None):
        d = null
        message = None
        firstRestricted = None

        self.expect_keyword('tabe')
        if identifier_is_optional or not self.match('('):
            token = self.lookahead
            d = self.parse_variable_identifier()
            if self.strict:
                if is_restricted_word(token['value']):
                    self.tolerate_unexpected_token(token, Messages.StrictFunctionName)
            else:
                if is_restricted_word(token['value']):
                    firstRestricted = token
                    message = Messages.StrictFunctionName
                elif is_strict_mode_reserved_word(token['value']):
                    firstRestricted = token
                    message = Messages.StrictReservedWord

        tmp = self.parse_params(firstRestricted)
        params = tmp['params']
        defaults = tmp['defaults']
        stricted = tmp.get('stricted')
        firstRestricted = tmp['firstRestricted']
        if tmp.get('message'):
            message = tmp['message']

        previousStrict = self.strict
        body = self.parse_function_source_elements()
        if self.strict and firstRestricted:
            self.throw_unexpected_token(firstRestricted, message)

        if self.strict and stricted:
            self.tolerate_unexpected_token(stricted, message)
        self.strict = previousStrict

        return node.finish_function_declaration(d, params, defaults, body)

    def parse_function_expression(self):
        id = null
        node = Node()
        firstRestricted = None
        message = None

        self.expect_keyword('tabe')

        if not self.match('('):
            token = self.lookahead
            id = self.parse_variable_identifier()
            if self.strict:
                if is_restricted_word(token['value']):
                    self.tolerate_unexpected_token(token, Messages.StrictFunctionName)
            else:
                if is_restricted_word(token['value']):
                    firstRestricted = token
                    message = Messages.StrictFunctionName
                elif is_strict_mode_reserved_word(token['value']):
                    firstRestricted = token
                    message = Messages.StrictReservedWord
        tmp = self.parse_params(firstRestricted)
        params = tmp['params']
        defaults = tmp['defaults']
        stricted = tmp.get('stricted')
        firstRestricted = tmp['firstRestricted']
        if tmp.get('message'):
            message = tmp['message']

        previousStrict = self.strict
        body = self.parse_function_source_elements()
        if self.strict and firstRestricted:
            self.throw_unexpected_token(firstRestricted, message)
        if self.strict and stricted:
            self.tolerate_unexpected_token(stricted, message)
        self.strict = previousStrict

        return node.finish_function_expression(id, params, defaults, body)

    # todo Translate parse class functions!

    def parse_class_expression(self):
        raise NotImplementedError()

    def parse_class_declaration(self):
        raise NotImplementedError()

    # 14 Program

    def parse_script_body(self):
        body = []
        firstRestricted = None

        while self.startIndex < self.length:
            token = self.lookahead
            if token['type'] != Token.StringLiteral:
                break
            statement = self.parse_statement_listItem()
            body.append(statement)
            if statement.expression.type != Syntax.Literal:
                # this is not directive
                break
            directive = self.source[token['start'] + 1: token['end'] - 1]
            if directive == 'use strict':
                self.strict = true
                if firstRestricted:
                    self.tolerate_unexpected_token(firstRestricted, Messages.StrictOctalLiteral)
            else:
                if not firstRestricted and token.get('octal'):
                    firstRestricted = token
        while self.startIndex < self.length:
            statement = self.parse_statement_listItem()
            # istanbul ignore if
            if statement is None:
                break
            body.append(statement)
        return body

    def parse_program(self):
        self.peek()
        node = Node()

        body = self.parse_script_body()
        return node.finishProgram(body)

    # DONE!!!
    def parse(self, code, options=None):
        if options is None:
            options = {}
        if options:
            raise NotImplementedError('Options not implemented! You can only use default settings.')

        self.clean()
        self.source = unicode(code) + ' \n ; //END'  # I have to add it in order not to check for EOF every time
        self.index = 0
        self.lineNumber = 1 if len(self.source) > 0 else 0
        self.lineStart = 0
        self.startIndex = self.index
        self.startLineNumber = self.lineNumber
        self.startLineStart = self.lineStart
        self.length = len(self.source)
        self.lookahead = null
        self.state = {
            'allowIn': true,
            'labelSet': {},
            'inFunctionBody': false,
            'inIteration': false,
            'inSwitch': false,
            'lastCommentStart': -1,
            'curlyStack': [],
            'parenthesizedCount': None}
        self.sourceType = 'script'
        self.strict = false
        program = self.parse_program()
        return node_to_dict(program)


def parse(javascript_code):
    """Returns syntax tree of javascript_code.
       Same as PyJsParser().parse  For your convenience :) """
    p = FsParser()
    return p.parse(javascript_code)


if __name__ == '__main__':
    import time

    test_path = None
    if test_path:
        f = open(test_path, 'rb')
        x = f.read()
        f.close()
    else:
        x = 'motaghayer $ = "Hello!"'
    p = FsParser()
    t = time.time()
    res = p.parse(x)
    dt = time.time() - t + 0.000000001
    if test_path:
        print(len(res))
    else:
        pprint(res)
    print()
    print('Parsed everyting in', round(dt, 5), 'seconds.')
    print('Thats %d characters per second' % int(len(x) / dt))
