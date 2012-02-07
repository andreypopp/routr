"""

    routr.schema -- constrain routes
    ================================

"""

from re import compile as re_compile
from webob import exc
from colander import * # re-export

from routr.exc import InvalidRoutePattern, NoURLPatternMatched

__all__ = ("QueryParams", "Optional", "URLPattern")

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

class URLPattern(object):

    _type_re = re_compile("{([a-z]+)}")

    typ_typ_map = {
        "int": (Int(), "[0-9]+"),
        "": (String(), "[a-zA-Z_-]"),
        "str": (String(), "[a-zA-Z_-]"),
        "string": (String(), "[a-zA-Z_-]"),
    }

    def __init__(self, pattern):
        self.pattern = pattern
        (self._compiled,
         self._schema,
         self._names) = self.compile_pattern(pattern)

    def match(self, path_info):
        m = self._compiled.match(path_info)
        if not m:
            raise NoURLPatternMatched()
        groups = m.groupdict()
        args = tuple(groups[n] for n in self._names)
        try:
            return path_info[m.end():], self._schema.deserialize(args)
        except Invalid, e:
            raise NoURLPatternMatched()

    def compile_pattern(self, pattern):
        names = []
        compiled = ""
        schema = SchemaNode(Tuple())
        last = 0
        for n, m in enumerate(self._type_re.finditer(pattern)):
            compiled += pattern[last:m.start()]
            typ = m.group(1)
            if not typ in self.typ_typ_map:
                raise InvalidRoutePattern(pattern)
            t, r = self.typ_typ_map[typ]
            schema.add(SchemaNode(t))
            name = "_gpt%d" % n
            names.append(name)
            compiled += "(?P<%s>%s)" % (name, r)
            last = m.end()
        compiled += pattern[last:]
        return re_compile(compiled), schema, names
