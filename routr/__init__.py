"""

    routr -- define routes
    ======================

"""

import re
from urllib import urlencode
from pkg_resources import iter_entry_points

from webob.exc import HTTPException
from routr.utils import import_string, cached_property, join
from routr.exc import (
    NoMatchFound, NoURLPatternMatched, RouteGuarded,
    MethodNotAllowed, RouteConfigurationError, InvalidRoutePattern,
    RouteReversalError)

__all__ = (
    "Configuration", "route", "include", "plug", "Trace",
    "Route", "Endpoint", "RootEndpoint", "RouteGroup",
    "GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "TRACE", "PATCH")

GET = "GET"
POST = "POST"
PUT = "PUT"
DELETE = "DELETE"
HEAD = "HEAD"
OPTIONS = "OPTIONS"
TRACE = "TRACE"
PATCH = "PATCH"

_http_methods = set([GET, POST, PUT, DELETE, HEAD, OPTIONS, TRACE])

class Trace(object):
    """ Result of route matching

    Represents a trace of matched routes towards the last one called endpoint.

    :attr args:
        collected positional arguments
    :attr kwargs:
        collected keyword arguments
    :attr routes:
        a list of matched routes with the endpoint route being the last one
    :attr endpoint:
        matched endpoint route

    Attributes of :attr:`.endpoint` route are made available on trace itself.
    """

    def __init__(self, args, kwargs, routes, payload=None):
        self.__dict__["args"] = args
        self.__dict__["kwargs"] = kwargs
        self.__dict__["routes"] = routes
        self.__dict__["payload"] = payload or {}

    @property
    def endpoint(self):
        return self.routes[-1] if self.routes else None

    @property
    def target(self):
        return self.endpoint.target

    def __add__(self, tr):
        args = self.args + tr.args
        kwargs = dict(self.kwargs)
        kwargs.update(tr.kwargs)
        routes = list(self.routes)
        routes.extend(tr.routes)
        payload = dict(self.payload)
        payload.update(tr.payload)
        return self.__class__(args, kwargs, routes, payload)

    def __setattr__(self, name, value):
        self.payload[name] = value

    def __getattr__(self, name):
        if not name in self.payload:
            raise AttributeError(name)
        return self.payload[name]

class Route(object):
    """ Base class for routes

    :param cfg:
        configuration object
    :param guards:
        a list of guards
    :param pattern:
        pattern for URL pattern
    """

    def __init__(self, cfg, guards, pattern, **annotations):
        self.cfg = cfg
        self.guards = guards
        self.pattern = self.compile_pattern(pattern)
        self.annotations = annotations

    def compile_pattern(self, pattern):
        if not pattern:
            return None
        if not pattern.startswith("/"):
            pattern = "/" + pattern
        return URLPattern(pattern)

    def match_pattern(self, path_info):
        """ Match ``path_info`` against route's ``pattern``"""
        if self.pattern is None:
            return path_info, ()
        return self.pattern.match(path_info)

    def match_guards(self, request, trace):
        """ Match ``request`` against route's ``guards`` and accumulate result
        in ``trace``
        """
        for guard in self.guards:
            trace = guard(request, trace) or trace
        return trace

    def __call__(self, request):
        """ Try to match route against ``request``

        If no route was matched the :class:`routr.exc.NoMatchFound` exception
        will be raised.

        :param request:
            :class:`webob.Request` object to match route against
        """
        path_info = self.cfg.extract_path_info(request)
        return self.match(path_info, request)

    def match(self, request):
        """ Match ``request`` against route

        return:
            trace object which accumulate ``*args`` and ``**kwargs``
        :rtype:
            :class:`.Trace`

        :raises routr.exc.NoURLPatternMatched:
            if no route was matched by URL
        :raises routr.exc.RouteGuarded:
            if route was guarded by one or more guards
        :raises routr.exc.MethodNotAllowed:
            if method isn't allowed for matched route
        """
        raise NotImplementedError()

    def reverse(self, name, *args, **kwargs):
        """ Reverse route with ``name`` using ``*args`` as pattern parameters
        and ``**kwargs`` as query string parameters

        :raises routr.exc.RouteReversalError:
            if no reversal can be computed for given arguments
        """
        raise NotImplementedError()

    def __iter__(self):
        raise NotImplementedError()

class Endpoint(Route):
    """ Endpoint route

    Associated with some object ``target`` which will be returned in case of
    successful match and a ``method`` which matches against request's method.

    Additional to :class:`.Route` params are:

    :param target:
        object to associate with route
    :param method:
        HTTP method associate with route
    :param name:
        optional name, should be provided if reversal of this route is needed,
        otherwise ``None`` is allowed
    """

    def __init__(self, target, method, name, cfg, guards, pattern, **annotations):
        super(Endpoint, self).__init__(cfg, guards, pattern, **annotations)
        self.target = target
        self.method = method
        self.name = name

    def match_method(self, request):
        if self.method != self.cfg.extract_method(request):
            raise MethodNotAllowed()

    def match(self, path_info, request):
        path_info, args = self.match_pattern(path_info)
        if path_info:
            raise NoURLPatternMatched()
        self.match_method(request)
        trace = self.cfg.trace(args, {}, [self])
        trace = self.match_guards(request, trace)
        return trace

    def reverse(self, name, *args, **kwargs):
        if name != self.name:
            raise RouteReversalError("no route with name '%s'" % name)
        url = self.pattern.reverse(*args) if self.pattern else "/"
        if kwargs:
            url += "?" + urlencode(kwargs)
        return url

    def __iter__(self):
        return iter([self])

    def __repr__(self):
        return "%s(target=%r, guards=%r, pattern=%r)" % (
            self.__class__.__name__, self.target, self.guards,
            self.pattern.pattern if self.pattern else None)

    __str__ = __repr__

class RootEndpoint(Endpoint):
    """ Endpoint route with no pattern"""

    def __init__(self, target, method, name, cfg, guards, **annotations):
        super(RootEndpoint, self).__init__(
            target, method, name, cfg, guards, None, **annotations)

    def match_pattern(self, path_info):
        if not path_info or path_info == "/":
            return "", ()
        raise NoURLPatternMatched()

class RouteGroup(Route):
    """ Route which represents a group of other routes

    Can have its own ``guards`` and a URL ``pattern``.

    Additional to :class:`.Route` params are:

    :param routes:
        a list of :class:`Route` objects
    """

    def __init__(self, routes, cfg, guards, pattern, **annotations):
        super(RouteGroup, self).__init__(cfg, guards, pattern, **annotations)
        self.routes = routes

    def index(self):
        """ Return mapping from route name to actual route"""
        idx = {}
        for r in self.routes:
            if isinstance(r, Endpoint) and r.name:
                if r.name in idx:
                    raise RouteConfigurationError(
                        "route this name '%s' already defined")
                if self.pattern or r.pattern:
                    idx[r.name] = self.pattern + r.pattern
                else:
                    idx[r.name] = URLPattern("/")
            elif isinstance(r, RouteGroup):
                ridx = r.index()
                if set(ridx) & set(idx):
                    raise RouteConfigurationError(
                        "route this name '%s' already defined")
                for (n, u) in ridx.items():
                    idx[n] = self.pattern + u
        return idx

    @cached_property
    def _cached_index(self):
        return self.index()

    def reverse(self, name, *args, **kwargs):
        if not name in self._cached_index:
            raise RouteReversalError("no route with name '%s'" % name)
        url = self._cached_index[name].reverse(*args)
        if kwargs:
            url += "?" + urlencode(kwargs)
        return url

    def match(self, path_info, request):
        path_info, args = self.match_pattern(path_info)
        guarded = []
        trace = self.cfg.trace(args, {}, [self])
        trace = self.match_guards(request, trace)
        for route in self.routes:
            try:
                subtrace = route.match(path_info, request)
            except NoURLPatternMatched:
                continue
            except MethodNotAllowed, e:
                guarded.append(RouteGuarded(e, e.response))
                continue
            except RouteGuarded, e:
                guarded.append(e)
                continue
            except HTTPException, e:
                guarded.append(RouteGuarded(e, e))
                continue
            else:
                return ((trace + subtrace)
                    if subtrace is not None and trace is not None
                    else trace or subtrace)
        if guarded:
            # NOTE we raise only last guard failure
            # cause it's more interesting one
            raise guarded[-1]
        raise NoURLPatternMatched()

    def __iter__(self):
        return iter(self.routes)

    def __repr__(self):
        return "%s(routes=%r, guards=%r, pattern=%r)" % (
            self.__class__.__name__, self.routes, self.guards, self.pattern)

    __str__ = __repr__

def parse_args(line):
    args = []
    kwargs = {}
    if not line:
        return args, kwargs
    for item in (a.strip() for a in line.split(",") if a):
        if "=" in item:
            k, v = item.split("=", 1)
            kwargs[k.strip()] = v.strip()
        else:
            args.append(item)
    return args, kwargs

def handle_str(args):
    if args:
        raise InvalidRoutePattern("'str' type doesn't accept args")
    return ("[^/]+", None)

def handle_path(args):
    if args:
        raise InvalidRoutePattern("'path' type doesn't accept args")
    return (".*", None)

def handle_int(args):
    if args:
        raise InvalidRoutePattern("'path' type doesn't accept args")
    return ("[0-9]+", int)

def handle_any(args):
    args, kwargs = parse_args(args)
    if not args:
        raise InvalidRoutePattern("'any' type requires positional args")
    if kwargs:
        raise InvalidRoutePattern("'any' doesn't accept keyword args")

    return ("(" + "|".join("(" + re.escape(x) + ")" for x in args) + ")", None)

class URLPattern(object):

    _type_re = re.compile("""
        {
        (?P<label>[a-z]+)            # label
        (:(?P<type>[a-z]+))?         # optional type identifier
        (\(                          # optional args
            (?P<args>[a-zA-Z= ,_]*)
        \))?
        }""", re.VERBOSE)


    _typemap = {
        None:       handle_str,
        "str":      handle_str,
        "string":   handle_str,
        "path":     handle_path,
        "int":      handle_int,
        "any":      handle_any,
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
        compiled = ""
        last = 0
        for n, m in enumerate(self._type_re.finditer(self.pattern)):
            compiled += re.escape(self.pattern[last:m.start()])
            typ, label, args = (
                m.group("type"), m.group("label"), m.group("args"))
            if not typ in self._typemap:
                raise InvalidRoutePattern(
                    "unknown type '%s' in pattern '%s'" % (typ, self.pattern))
            r, c = self._typemap[typ](args)
            name = "_gpt%d" % n
            names.append((name, c, label))
            compiled += "(?P<%s>%s)" % (name, r)
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
                " only %r was supplied" % (self.pattern, args))
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
        return URLPattern(join(self.pattern, o.pattern))

    def __radd__(self, o):
        if o is None:
            return self
        return URLPattern(join(o.pattern, self.pattern))

    def __repr__(self):
        return "<routr.URLPattern %s>" % self.pattern

def include(spec):
    """ Include routes by ``spec``

    :param spec:
        asset specification which points to :class:`.Route` instance
    """
    r = import_string(spec)
    if not isinstance(r, Route):
        raise RouteConfigurationError(
            "route included by '%s' isn't a route" % spec)
    return r

def plug(name):
    """ Plug routes by ``setuptools`` entry points, identified by ``name``

    :param name:
        entry point name to query routes
    """
    routes = []
    for p in iter_entry_points("routr", name=name):
        r = p.load()
        if not isinstance(r, Route):
            raise RouteConfigurationError(
                "entry point '%s' doesn't point at Route instance" % p)
        routes.append(r)
    return RouteGroup(routes, [])

class Configuration(object):
    """ Object which holds configuration for route definition DSL"""

    root = RootEndpoint
    endpoint = Endpoint
    group = RouteGroup
    trace = Trace

    def extract_method(self, request):
        """ Extract method of the ``request``"""
        return request.method

    def extract_path_info(self, request):
        """ Extract PATH_INFO of the ``request``"""
        return request.path_info

    def route(self, *directives, **kwargs):
        """ Directive for configuring routes in application

        :param directives:
            ([method,] [pattern,] target) produces endpoint route
            ([method,] [pattern,] *routes) produces route group
        :param kwargs:
            name and guards are treated as name and guards for routes, other
            keyword args a are passed as annotations
        """
        directives = list(directives)
        if not directives:
            raise RouteConfigurationError()

        if not directives:
            raise RouteConfigurationError()

        method = directives.pop(0) if directives[0] in _http_methods else None

        if not directives:
            raise RouteConfigurationError("empty routes")

        name = kwargs.pop("name", None)
        guards = kwargs.pop("guards", [])

        if not isinstance(guards, (list, tuple)):
            guards = [guards]

        # root directive
        if len(directives) == 1 and not isinstance(directives[0], Route):
            target = directives[0]
            return self.root(target, method or GET, name, self, guards, **kwargs)

        # endpoint directive
        elif (len(directives) == 2
                and isinstance(directives[0], str)
                and not isinstance(directives[1], Route)):
            pattern, target = directives
            return self.endpoint(
                target, method or GET, name, self, guards, pattern, **kwargs)

        # route list with pattern
        elif (len(directives) > 1
                and isinstance(directives[0], str)
                and all(isinstance(d, Route) for d in directives[1:])):
            pattern, routes = directives[0], directives[1:]
            if method:
                raise RouteConfigurationError(
                    "'method' doesn't make sense for route groups")
            return self.group(routes, self, guards, pattern, **kwargs)

        # route list
        elif all(isinstance(d, Route) for d in directives):
            if method:
                raise RouteConfigurationError(
                    "'method' doesn't make sense for route groups")
            return self.group(directives, self, guards, None, **kwargs)

        # error here
        else:
            # TODO: expand on this
            raise RouteConfigurationError("improper usage of 'route' directive")

config = Configuration()
route = config.route
