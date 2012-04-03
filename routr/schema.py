"""

    routr.schema -- constrain routes
    ================================

"""

from webob import exc
from colander import * # re-export

from routr.exc import InvalidRoutePattern, NoURLPatternMatched

__all__ = (
    "RequestParams", "FormParams", "QueryParams", "Optional",
    "opt", "qs", "form")

_none = object()

class Optional(object):

    none = _none

    def __init__(self, typ, default=_none):
        if isinstance(typ, type):
            typ = typ()
        self.typ = typ
        self.default = default

class RequestParams(object):
    """ Guard for query string parameters

    Raises :class:`webob.exc.HTTPBadRequest` if query string isn't validated.

    :param kwargs:
        mapping with validators for query string
    """

    def __init__(self, **kwargs):
        self.schema = SchemaNode(Mapping())
        self.post_processor = None
        for name, typ in kwargs.items():
            if isinstance(typ, SchemaNode):
                typ = typ.clone()
                typ.name = name
                self.schema.add(typ)
                continue
            if isinstance(typ, Optional):
                self.schema.add(SchemaNode(
                    typ.typ,
                    name=name,
                    missing=typ.default))
            else:
                if isinstance(typ, type):
                    typ = typ()
                self.schema.add(SchemaNode(typ, name=name))

    def params(self, request):
        raise NotImplementedError()

    def then(self, post_processor):
        self.post_processor = post_processor
        return self

    def __call__(self, request, trace):
        try:
            kwargs = self.schema.deserialize(self.params(request))
        except Invalid, e:
            raise exc.HTTPBadRequest(e)
        for k, v in kwargs.items():
            if v is Optional.none:
                kwargs.pop(k)
        if self.post_processor:
            kwargs = self.post_processor(kwargs)
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

class QueryParams(RequestParams):

    def params(self, request):
        return request.GET

class FormParams(RequestParams):

    def params(self, request):
        return request.POST

qs = QueryParams
form = FormParams
opt = Optional
