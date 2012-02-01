""" ``routr.schema``"""

from webob import exc
from colander import * # re-export

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
