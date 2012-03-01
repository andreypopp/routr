"""

    routr.schema -- constrain routes
    ================================

"""

from webob import exc
from colander import * # re-export

from routr.exc import InvalidRoutePattern, NoURLPatternMatched

__all__ = ("QueryParams", "Optional")

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

    Raises :class:`webob.exc.HTTPBadRequest` if query string isn't validated.

    :param kwargs:
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

    def __call__(self, request, trace):
        try:
            kwargs = self.schema.deserialize(request.GET)
        except Invalid, e:
            raise exc.HTTPBadRequest(e)
        for k, v in kwargs.items():
            if v is Optional.none:
                kwargs.pop(k)
        trace.kwargs.update(kwargs)
        return trace

    def __add__(self, o):
        s = SchemaNode(Mapping())
        for c in self.schema.children:
            s.add(c)
        for c in o.schema.children:
            s.add(c)
        r = QueryParams()
        r.schema = s
        return r
