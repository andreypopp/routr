"""

    routr.schema2 -- schema validation
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from webob.exc import HTTPBadRequest

__all__ = ('validate', 'opt', 'ValidationError')


class ValidationError(ValueError):
    """ Validation error"""

    def __init__(self, error):
        self.error = error
        super(ValueError, self).__init__(error)

def validate(schema, data):

    if isinstance(schema, tuple) and hasattr(schema, '_replace'):
        result = validate(schema._asdict(), data)
        return type(schema)(**result)

    if isinstance(schema, dict):
        result, errors = {}, {}
        for k, v in schema.items():
            if not k in data:
                if not isinstance(v, opt):
                    errors[k] = 'missing %s key' % k
                elif v.default is not _no_default:
                    result[k] = v.default
                continue
            if isinstance(v, opt):
                v = v.type
            try:
                result[k] = validate(v, data[k])
            except ValidationError as e:
                errors[k] = e.error

        if errors:
            raise ValidationError(errors)

        return result

    elif isinstance(schema, list):
        assert len(schema) == 1, 'invalid schema'
        return [validate(schema[0], v) for v in data]

    elif isinstance(schema, tuple):
        if not len(schema) == len(data):
            raise ValidationError('length should be equal to %d' % len(schema))
        return tuple(validate(s, v) for s, v in zip(schema, data))

    else:
        try:
            return schema(data)
        except ValueError as e:
            raise ValidationError(str(e))

_no_default = object()

class opt(object):
    """ Marker for optional elements in container"""

    def __init__(self, type, default=_no_default):
        self.type = type
        self.default = default

class RequestParams(object):

    def __init__(self, **fields):
        self.schema = fields

    def params(self, request):
        raise NotImplementedError()

    def __call__(self, request, trace):
        params = self.params(request)
        try:
            result = validate(self.schema, params)
        except ValidationError as e:
            raise HTTPBadRequest(e.error)
        else:
            trace.kwargs.update(result)

class qs(RequestParams):

    def params(self, request):
        return request.GET

class form(RequestParams):

    def params(self, request):
        return request.POST
