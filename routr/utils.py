"""

    routr.utilities -- utility code
    ===============================

"""

import types
import inspect
import sys

__all__ = (
    'import_string', 'cached_property', 'ImportStringError', 'join',
    'positional_args', 'inject_args')

class cached_property(object):
    """ Just like ``property`` but computed only once"""

    def __init__(self, func):
        self.func = func
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__

    def __get__(self, obj, cls):
        if obj is None:
            return self
        val = self.func(obj)
        obj.__dict__[self.__name__] = val
        return val

def import_string(import_name, silent=False):
    """Imports an object based on a string.  This is useful if you want to
    use import paths as endpoints or something similar.  An import path can
    be specified either in dotted notation (``xml.sax.saxutils.escape``)
    or with a colon as object delimiter (``xml.sax.saxutils:escape``).

    If `silent` is True the return value will be `None` if the import fails.

    For better debugging we recommend the new :func:`import_module`
    function to be used instead.

    :param import_name: the dotted name for the object to import.
    :param silent: if set to `True` import errors are ignored and
                   `None` is returned instead.
    :return: imported object

    :copyright: (c) 2011 by the Werkzeug Team
    """
    # force the import name to automatically convert to strings
    if isinstance(import_name, unicode):
        import_name = str(import_name)
    try:
        if ':' in import_name:
            module, obj = import_name.split(':', 1)
        elif '.' in import_name:
            module, obj = import_name.rsplit('.', 1)
        else:
            return __import__(import_name)
        # __import__ is not able to handle unicode strings in the fromlist
        # if the module is a package
        if isinstance(obj, unicode):
            obj = obj.encode('utf-8')
        try:
            return getattr(__import__(module, None, None, [obj]), obj)
        except (ImportError, AttributeError):
            # support importing modules not yet set up by the parent module
            # (or package for that matter)
            modname = module + '.' + obj
            __import__(modname)
            return sys.modules[modname]
    except ImportError, e:
        if not silent:
            raise ImportStringError(import_name, e), None, sys.exc_info()[2]

class ImportStringError(ImportError):
    """Provides information about a failed :func:`import_string` attempt.

    :copyright: (c) 2011 by the Werkzeug Team
    """

    #: String in dotted notation that failed to be imported.
    import_name = None
    #: Wrapped exception.
    exception = None

    def __init__(self, import_name, exception):
        self.import_name = import_name
        self.exception = exception

        msg = (
            'import_string() failed for %r. Possible reasons are:\n\n'
            '- missing __init__.py in a package;\n'
            '- package or module path not included in sys.path;\n'
            '- duplicated package or module name taking precedence in '
            'sys.path;\n'
            '- missing module, class, function or variable;\n\n'
            'Debugged import:\n\n%s\n\n'
            'Original exception:\n\n%s: %s')

        name = ''
        tracked = []
        for part in import_name.replace(':', '.').split('.'):
            name += (name and '.') + part
            imported = import_string(name, silent=True)
            if imported:
                tracked.append((name, imported.__file__))
            else:
                track = ['- %r found in %r.' % (n, i) for n, i in tracked]
                track.append('- %r not found.' % name)
                msg = msg % (import_name, '\n'.join(track),
                             exception.__class__.__name__, str(exception))
                break

        ImportError.__init__(self, msg)

    def __repr__(self):
        return '<%s(%r, %r)>' % (self.__class__.__name__, self.import_name,
                                 self.exception)

def join(a, b):
    """ Join two URL parts

        >>> join('/a/', '/b/')
        '/a/b/'

    """
    a = a or ''
    b = b or ''
    return a.rstrip('/') + '/' + b.lstrip('/')

def positional_args(obj):
    """ Return ordered list of positional args with which ``obj`` can be called

    :param obj:
        can be a plain function (or lambda) or some type object or method or
        simply callable object (with __call__ method defined)
    """
    if isinstance(obj, types.FunctionType):
        return _positional_args(obj)
    if isinstance(obj, type):
        obj = obj.__init__
    elif isinstance(obj, types.MethodType):
        pass
    elif hasattr(obj, '__call__'):
        obj = obj.__call__
    args = _positional_args(obj)
    if 'self' in args:
        args.remove('self')
    return args

def _positional_args(func):
    argspec = inspect.getargspec(func)
    return (argspec.args[:-len(argspec.defaults)]
        if argspec.defaults
        else argspec.args)

def inject_args(obj, args, **injections):
    """ Inject args for given callable ``obj``, ``args`` with ``injections``"""
    args = list(args)
    pos_args = positional_args(obj)
    for k, arg in injections.items():
        if k in pos_args:
            args.insert(pos_args.index(k), arg)
    return args
