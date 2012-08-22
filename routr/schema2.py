"""

    routr.schema2 -- schema validation
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

__all__ = ('qs', 'form', 'validate')

def qs(**fields):
    pass

def form(**fields):
    pass

def validate(schema, data):
    if isinstance(schema, dict):
        return {k: validate(s, data.get(k)) for k, s in schema.items()}
    elif isinstance(schema, list):
        return [validate(schema[0], v) for v in data]
    elif isinstance(schema, tuple):
        return tuple(validate(s, v) for s, v in zip(schema, data))
    else:
        return schema(data)

