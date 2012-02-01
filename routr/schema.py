""" ``routr.schema``"""

from re import compile as re_compile
from webob import exc
from colander import * # re-export

from routr.exc import InvalidRoutePattern, RouteNotFound

__all__ = ("QueryParams", "Optional", "Method")

_none = object()

class Optional(object):

    none = _none

    def __init__(self, typ, default=_none):
        if isinstance(typ, type):
            typ = typ()
        self.typ = typ
        self.default = default

class QueryParams(object):
    """ Guard for query string parameters

    Raises :class:``webob.exc.HTTPBadRequest`` if query string isn't validated.

    :param **kwargs:
        mapping with validators for query string
    """

    def __init__(self, **kwargs):
        self.schema = SchemaNode(Mapping())
        for name, typ in kwargs.items():
            if isinstance(typ, Optional):
                self.schema.add(SchemaNode(
                    typ.typ,
                    name=name,
                    missing=typ.default))
            else:
                if isinstance(typ, type):
                    typ = typ()
                self.schema.add(SchemaNode(typ, name=name))

    def __call__(self, request):
        try:
            kwargs = self.schema.deserialize(request.GET)
        except Invalid, e:
            raise exc.HTTPBadRequest(e)
        for k, v in kwargs.items():
            if v is Optional.none:
                kwargs.pop(k)
        return kwargs

class Method(object):
    """ Guard for HTTP method

    Raises :class:``webob.exc.HTTPMethodNotAllowed`` if method isn't validated.

    :param *allowed:
        allowed HTTP method
    """

    def __init__(self, *allowed):
        self.allowed = allowed

    def __call__(self, request):
        if not request.method in self.allowed:
            raise exc.HTTPMethodNotAllowed()

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, ", ".join(self.allowed))

class URLPattern(object):

    _type_re = re_compile("{([a-z]+)}")

    typ_typ_map = {
        "int": (Int(), "[0-9]+"),
        "": (String(), "[a-zA-Z_-]"),
        "str": (String(), "[a-zA-Z_-]"),
        "string": (String(), "[a-zA-Z_-]"),
    }

    def __init__(self, pattern):
        self._c = 0
        self._names = []
        self.pattern, self.schema = self.compile_pattern(pattern)

    def match(self, path_info):
        m = self.pattern.match(path_info)
        if not m:
            raise RouteNotFound()
        groups = m.groupdict()
        args = tuple(groups[n] for n in self._names)
        try:
            return path_info[m.end():], self.schema.deserialize(args)
        except Invalid, e:
            raise RouteNotFound()

    def compile_pattern(self, pattern):
        compiled = ""
        schema = SchemaNode(Tuple())
        last = 0
        for m in self._type_re.finditer(pattern):
            compiled += pattern[last:m.start()]
            typ = m.group(1)
            if not typ in self.typ_typ_map:
                raise InvalidRoutePattern(pattern)
            t, r = self.typ_typ_map[typ]
            self._c = self._c + 1
            name = "_gpt%d" % self._c
            schema.add(SchemaNode(t))
            self._names.append(name)
            compiled += "(?P<%s>%s)" % (name, r)
            last = m.end()
        compiled += pattern[last:]
        return re_compile(compiled), schema
