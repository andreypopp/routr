"""

    routr.urlpattern -- matching URL against pattern
    ================================================

"""

import re

from routr.utils import cached_property, join
from routr.exc import (
        InvalidRoutePattern, RouteReversalError, NoURLPatternMatched)

__all__ = ('URLPattern',)

def parse_args(line):
    args = []
    kwargs = {}
    if not line:
        return args, kwargs
    for item in (a.strip() for a in line.split(',') if a):
        if '=' in item:
            k, v = item.split('=', 1)
            kwargs[k.strip()] = v.strip()
        else:
            args.append(item)
    return args, kwargs

def handle_str(args):
    args, kwargs = parse_args(args)
    re = kwargs.pop('re', None)
    if kwargs or args:
        raise InvalidRoutePattern("invalid args for 'str' type")
    if re:
        return (re + '(?=$|/)', None)
    return ('[^/]+', None)

def handle_path(args):
    if args:
        raise InvalidRoutePattern("'path' type doesn't accept args")
    return ('.*', None)

def handle_int(args):
    if args:
        raise InvalidRoutePattern("'path' type doesn't accept args")
    return ('[0-9]+', int)

def handle_any(args):
    args, kwargs = parse_args(args)
    if not args:
        raise InvalidRoutePattern("'any' type requires positional args")
    if kwargs:
        raise InvalidRoutePattern("'any' doesn't accept keyword args")

    return ('(' + '|'.join('(' + re.escape(x) + ')' for x in args) + ')', None)

class URLPattern(object):

    _type_re = re.compile("""
        {
        (?P<label>[a-zA-Z][a-zA-Z0-9]*)     # label
        (:(?P<type>[a-zA-Z][a-zA-Z0-9]*))?  # optional type identifier
        (\(                                 # optional args
            (?P<args>[a-zA-Z= ,_\[\]\+\-0-9\{\}]*)
        \))?
        }""", re.VERBOSE)


    typemap = {
        None:       handle_str,
        'str':      handle_str,
        'string':   handle_str,
        'path':     handle_path,
        'int':      handle_int,
        'any':      handle_any,
    }

    def __init__(self, pattern):
        self.pattern = pattern

        self._compiled = None
        self._names = None

    @cached_property
    def is_exact(self):
        return self._type_re.search(self.pattern) is None

    @cached_property
    def compiled(self):
        if self._compiled is None:
            self.compile()
        return self._compiled

    @cached_property
    def _pattern_len(self):
        return len(self.pattern)

    def compile(self):
        if self.is_exact:
            return

        names = []
        compiled = ''
        last = 0
        for n, m in enumerate(self._type_re.finditer(self.pattern)):
            compiled += re.escape(self.pattern[last:m.start()])
            typ, label, args = (
                m.group('type'), m.group('label'), m.group('args'))
            if not typ in self.typemap:
                raise InvalidRoutePattern(
                    "unknown type '%s' in pattern '%s'" % (typ, self.pattern))
            r, c = self.typemap[typ](args)
            name = '_gpt%d' % n
            names.append((name, c, label))
            compiled += '(?P<%s>%s)' % (name, r)
            last = m.end()
        compiled += re.escape(self.pattern[last:])

        self._compiled = re.compile(compiled)
        self._names = names

    def reverse(self, *args):
        if self.is_exact:
            return self.pattern

        r = self.pattern
        for arg in args:
            r = self._type_re.sub(str(arg), r, 1)
        if self._type_re.search(r):
            raise RouteReversalError(
                "not enough params for reversal of '%s' route,"
                ' only %r was supplied' % (self.pattern, args))
        return r

    def match(self, path_info):
        if self.is_exact:
            if not path_info.startswith(self.pattern):
                raise NoURLPatternMatched(path_info)
            return path_info[self._pattern_len:], ()

        m = self.compiled.match(path_info)
        if not m:
            raise NoURLPatternMatched("no match for '%s' against '%s'" % (
                path_info, self._compiled.pattern))
        groups = m.groupdict()
        try:
            args = tuple(
                c(groups[n]) if c else groups[n]
                for (n, c, l) in self._names)
        except ValueError:
            raise NoURLPatternMatched()
        return path_info[m.end():], args

    def __add__(self, o):
        if o is None:
            return self
        return self.__class__(join(self.pattern, o.pattern))

    def __radd__(self, o):
        if o is None:
            return self
        return self.__class__(join(o.pattern, self.pattern))

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.pattern)
