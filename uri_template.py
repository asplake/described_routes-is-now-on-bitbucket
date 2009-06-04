import urllib
import re

'''
Regexp-based implementation of URI Templates v3.

Features:

1) A partial expansion mode inspired by sporkonger/addressable (rubygem)
2) Overridable quoting of special charactors

Usage:

>>> import uri_template
>>> uri_template.sub("http://example.com/users/{user_id}{-prefix|.|format}", {'user_id': 'dojo'})
"http://example.com/users/dojo"

Limitations:

There are two specified features not supported in this initial version:
1) default values (e.g. {foo=FOO})
2) list-valued parameters to the prefix and suffic operators, e.g. uri_template.sub("/path-to{-suffix|/|foo}", {'foo': ['a', 'b']})

Author:

Mike Burrows (asplake), email mailto:mjb@asplake.co.uk, website http://positiveincline.com (see articles tagged uri[http://positiveincline.com/?tag=uri])
'''

def sub(template, params, encoding=urllib.quote, partial=False):
    return re.sub(r'{(-)?([^}]+)}', lambda match: matched(match, params, encoding, partial), template)

def matched(match, params, encoding, partial):
    is_operator, body = match.groups()
    if is_operator: # leading '-'
        operator, arg, operands = re.split(r'\|', body)
        variables = re.split(',', operands)
        return operators[operator](arg, variables, params, encoding, partial)
    else:
        return operators['variable'](body, params, encoding, partial)

def single_variable(variables):
    if len(variables) != 1:
        raise TypeError('-prefix takes exactly one variable, given %s' % ','.join(variables))
    return variables[0]
    
def encoded_lookup(params, variable, encoding):
    return encoding(params[variable])

operators = {}

def operator(name):
    def save_operator(func):
        operators[name] = func
        return func
    return save_operator

@operator('variable')
def do_variable(variable, params, encoding, partial):
    if variable in params:
        return encoded_lookup(params, variable, encoding)
    elif partial:
        return '{%s}' % variable
    else:
        return ''

@operator('opt')
def op_opt(arg, variables, params, encoding, partial):
    if [variable for variable in variables if variable in params and params[variable] != []]:
        return arg
    elif partial:
        return '{-opt|%s|%s}' % (arg, ','.join(variables))
    else:
        return ''

@operator('neg')
def op_neg(arg, variables, params, encoding, partial):
    if [variable for variable in variables if variable in params and params[variable] != []]:
        return ''
    elif partial:
        return '{-neg|%s|%s}' % (arg, ','.join(variables))
    else:
        return arg

@operator('prefix')
def op_prefix(prefix, variables, params, encoding, partial):
    variable = single_variable(variables)
    if variable in params:
        return prefix + encoded_lookup(params, variable, encoding)
    elif partial:
        return '{-prefix|%s|%s}' % (prefix, variable)
    else:
        return ''

@operator('suffix')
def op_suffix(suffix, variables, params, encoding, partial):
    variable = single_variable(variables)
    if variable in params:
        return encoded_lookup(params, variable, encoding) + suffix
    elif partial:
        return '{-suffix|%s|%s}' % (suffix, variable)
    else:
        return ''

@operator('join')
def op_join(separator, variables, params, encoding, partial):
    if not partial:
        return separator.join(variable + '=' + encoded_lookup(params, variable, encoding) for variable in variables if variable in params)
    else:
        buf = ''
        deferred = []
        filled = False
        for variable in variables:
            if variable in params:
                if deferred:
                    if filled:
                        if len(deferred) == 1:
                            buf += '{-prefix|%s%s=|%s}' % (separator, deferred[0], deferred[0])
                        else:
                            buf += '{-opt|%s|%s}{-join|%s|%s}' % (separator, ','.join(deferred), separator, ','.join(deferred))
                    else:
                        buf += '{-join|%s|%s}{-opt|%s|%s}' % (separator, ','.join(deferred), separator, ','.join(deferred))
                    deferred = []
                if filled:
                    buf += separator
                buf += '%s=%s' % (variable, encoded_lookup(params, variable, encoding))
                filled = True
            else:
                deferred.append(variable)
        if deferred:
            if filled:
                if len(deferred) == 1:
                    buf += '{-prefix|%s%s=|%s}' % (separator, deferred[0], deferred[0])
                else:
                    buf += '{-opt|%s|%s}{-join|%s|%s}' % (separator, ','.join(deferred), separator, ','.join(deferred))
            else:
                buf += '{-join|%s|%s}' % (separator, ','.join(deferred))
        return buf

@operator('list')
def op_list(separator, variables, params, encoding, partial):
    variable = single_variable(variables)
    if variable in params:
        return separator.join(map(encoding, params[variable]))
    elif partial:
        return '{-list|%s|%s}' % (separator, variable)
    else:
        ''

if __name__ == '__main__':
    import unittest
    
    # Acknowledgement: the first set of unit tests is based on Joe Gregorio's (in turn based on examples in his v3 spec)
    # Note: the commented-out examples aren't yets supported (see "Limitations")
    
    testdata = [
        ('/path/to/{foo}',                          {},                            '/path/to/'),
        ('/path/to/{foo}',                          {'foo': 'barney'},             '/path/to/barney'),
#        ('/path/to/{foo=wilma}',                    {},                            '/path/to/wilma'),
#        ('/path/to/{foo=wilma}',                    {'foo': 'barney'},             '/path/to/barney'),
        ('/path/to/{foo}',                          {'foo': 'barney'},             '/path/to/barney'),

        ('/path/to/{-prefix|&|foo}',                {},                            '/path/to/'),
#        ('/path/to/{-prefix|&|foo=wilma}',          {},                            '/path/to/&wilma'),
#        ('/path/to/{-prefix||foo=wilma}',           {},                            '/path/to/wilma'),
#        ('/path/to/{-prefix|&|foo=wilma}',          {'foo': 'barney'},             '/path/to/&barney'),
#        ('/path/to/{-prefix|&|foo}',                {'foo': ['wilma', 'barney']},  '/path/to/&wilma&barney'),
        ('/path/to/{-prefix|&|foo}',                {'foo': 'barney'},             '/path/to/&barney'),

        ('/path/to/{-suffix|/|foo}',                {},                            '/path/to/'),
#        ('/path/to/{-suffix|#|foo=wilma}',          {},                            '/path/to/wilma#'),
#        ('/path/to/{-suffix|&?|foo=wilma}',         {'foo': 'barney'},             '/path/to/barney&?'),
#        ('/path/to/{-suffix|&|foo}',                {'foo': ['wilma', 'barney']},  '/path/to/wilma&barney&'),
        ('/path/to/{-suffix|&?|foo}',               {'foo': 'barney'},             '/path/to/barney&?'),

        ('/path/to/{-join|/|foo}',                  {},                            '/path/to/'),
        ('/path/to/{-join|/|foo,bar}',              {},                            '/path/to/'),
        ('/path/to/{-join|&|q,num}',                {},                            '/path/to/'),
#        ('/path/to/{-join|#|foo=wilma}',            {},                            '/path/to/foo=wilma'),
#        ('/path/to/{-join|#|foo=wilma,bar}',        {},                            '/path/to/foo=wilma'),
#        ('/path/to/{-join|#|foo=wilma,bar=barney}', {},                            '/path/to/foo=wilma#bar=barney'),
#        ('/path/to/{-join|&?|foo=wilma}',           {'foo': 'barney'},             '/path/to/foo=barney'),
        ('/path/to/{-join|&?|foo}',                 {'foo': 'barney'},             '/path/to/foo=barney'),

        ('/path/to/{-list|/|foo}',                  {},                            '/path/to/'),
        ('/path/to/{-list|/|foo}',                  {'foo': ['a', 'b']},           '/path/to/a/b'),
        ('/path/to/{-list||foo}',                   {'foo': ['a', 'b']},           '/path/to/ab'),
        ('/path/to/{-list|/|foo}',                  {'foo': ['a']},                '/path/to/a'),
        ('/path/to/{-list|/|foo}',                  {'foo': []},                   '/path/to/'),

        ('/path/to/{-opt|&|foo}',                   {},                            '/path/to/'),
        ('/path/to/{-opt|&|foo}',                   {'foo': 'fred'},               '/path/to/&'),
        ('/path/to/{-opt|&|foo}',                   {'foo': []},                   '/path/to/'),
        ('/path/to/{-opt|&|foo}',                   {'foo': ['a']},                '/path/to/&'),
        ('/path/to/{-opt|&|foo,bar}',               {'foo': ['a']},                '/path/to/&'),
        ('/path/to/{-opt|&|foo,bar}',               {'bar': 'a'},                  '/path/to/&'),
        ('/path/to/{-opt|&|foo,bar}',               {},                            '/path/to/'),

        ('/path/to/{-neg|&|foo}',                   {},                            '/path/to/&'),
        ('/path/to/{-neg|&|foo}',                   {'foo': 'fred'},               '/path/to/'),
        ('/path/to/{-neg|&|foo}',                   {'foo': []},                   '/path/to/&'),
        ('/path/to/{-neg|&|foo}',                   {'foo': ['a']},                '/path/to/'),
        ('/path/to/{-neg|&|foo,bar}',               {'bar': 'a'},                  '/path/to/'),
        ('/path/to/{-neg|&|foo,bar}',               {'bar': []},                   '/path/to/&'),

        ('/path/to/{foo}',                          {'foo': ' '},                  '/path/to/%20'),
        ('/path/to/{-list|&|foo}',                  {'foo': ['&', '&', '|', '_']}, '/path/to/%26&%26&%7C&_')]
        
    t = '/{foo}-{foo=def}-{-opt|opt|foo}-{-neg|neg|foo}{-prefix|pre|foo}-{-suffix|suf|foo}&{-join|&|foo,bar,baz}'
    test_partial_params = [
        {'foo': 'FOO', 'bar': 'BAR', 'baz': 'BAZ'},
        {'bar': 'BAR', 'baz': 'BAZ'},
        {'foo': 'FOO', 'baz': 'BAZ'},
        {'foo': 'FOO', 'bar': 'BAR'},
        {'foo': 'FOO'},
        {'bar': 'BAR'},
        {'baz': 'BAZ'}]
        
    class TestUriTemplates(unittest.TestCase):
        def test_operators(self):
            for template, params, expected in testdata:
                self.assertEqual(expected, sub(template, params), " ".join(["testing", repr(template), repr(params)]))
        
        def test_partial(self):
            print 'test_partial'
            for params in test_partial_params:
                expected = sub(t, params)
                self.assertEqual(expected, sub(sub(t, {}, partial=True), params), "testing (1) " + repr(params))
                self.assertEqual(expected, sub(sub(t, params, partial=True), {}), "testing (2) " + repr(params))

    unittest.main()
