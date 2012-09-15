"""

    routr -- routing engine for WebOb based WSGI applications
    =========================================================

    This module provides data structures along with easy-to-use DSLish API to
    define complex routing rules for WSGI applications based on WebOb.

"""

import re
from urllib import urlencode
from pkg_resources import iter_entry_points

from webob.exc import HTTPException, HTTPBadRequest
from routr.utils import import_string, cached_property
from routr.urlpattern import URLPattern
from routr.exc import (
    NoMatchFound, NoURLPatternMatched, RouteGuarded,
    MethodNotAllowed, RouteConfigurationError, InvalidRoutePattern,
    RouteReversalError)

__all__ = (
    'Configuration', 'route', 'include', 'plug', 'Trace',
    'Route', 'Endpoint', 'RouteGroup', 'HTTPMethod',
    'GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS', 'TRACE', 'PATCH',
    'NoMatchFound', 'RouteConfigurationError')

class HTTPMethod(str):
    """ HTTP method

    Objects of this type represent HTTP method constants. They are also callable
    -- work as a shortcut for defining route with corresponding method --
    ``route(GET, ...)`` equivalent to ``GET(...)``.
    """

    def __call__(self, *args, **kwargs):
        return route(self, *args, **kwargs)

GET     = HTTPMethod('GET')
POST    = HTTPMethod('POST')
PUT     = HTTPMethod('PUT')
DELETE  = HTTPMethod('DELETE')
HEAD    = HTTPMethod('HEAD')
OPTIONS = HTTPMethod('OPTIONS')
TRACE   = HTTPMethod('TRACE')
PATCH   = HTTPMethod('PATCH')

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
    """

    def __init__(self, args, kwargs, routes, payload=None):
        self.__dict__['payload'] = payload or {
            'args': args,
            'kwargs': kwargs,
            'routes': routes
        }

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
        payload.update({
            'args': args,
            'kwargs': kwargs,
            'routes': routes,
            })
        return self.__class__(args, kwargs, routes, payload)

    def __setattr__(self, name, value):
        self.payload[name] = value

    def __getattr__(self, name):
        if not name in self.payload:
            raise AttributeError(name)
        return self.payload[name]

class Route(object):
    """ Base class for routes

    :param guards:
        a list of guards
    :param pattern:
        pattern for URL pattern
    :param url_pattern_cls:
        class which should be used for URL pattern matching (default to
        :class:`.urlpattern.URLPattern`
    :param annotations:
        various annotations
    """

    url_pattern_cls = None

    def __init__(self, guards, pattern, url_pattern_cls=None, **annotations):
        self.guards = guards
        self._pattern = pattern
        self.url_pattern_cls = url_pattern_cls
        self.annotations = annotations

    @cached_property
    def pattern(self):
        """ Compiled pattern"""
        return self.compile_pattern(self._pattern)

    def compile_pattern(self, pattern):
        if not pattern:
            return None
        if not pattern.startswith('/'):
            pattern = '/' + pattern
        return (self.url_pattern_cls or URLPattern)(pattern)

    def match_pattern(self, path_info):
        """ Match ``path_info`` against route's ``pattern``"""
        if self.pattern is None:
            if not path_info or path_info == '/':
                return '', ()
            raise NoURLPatternMatched()
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
        return self.match(request.path_info, request)

    def match(self, path_info, request):
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

    def __init__(self, target, method, name, guards, pattern,
            **annotations):
        super(Endpoint, self).__init__(guards, pattern, **annotations)
        self.target = target
        self.method = method
        self.name = name

    def match_method(self, request):
        if self.method != request.method:
            raise MethodNotAllowed()

    def match(self, path_info, request):
        path_info, args = self.match_pattern(path_info)
        if path_info:
            raise NoURLPatternMatched()
        self.match_method(request)
        trace = Trace(args, {}, [self])
        trace = self.match_guards(request, trace)
        return trace

    def reverse(self, name, *args, **kwargs):
        if name != self.name:
            raise RouteReversalError("no route with name '%s'" % name)
        url = self.pattern.reverse(*args) if self.pattern else '/'
        if kwargs:
            url += '?' + urlencode(kwargs)
        return url

    def __iter__(self):
        return iter([self])

    def __repr__(self):
        return '%s(target=%r, guards=%r, pattern=%r)' % (
            self.__class__.__name__, self.target, self.guards,
            self.pattern.pattern if self.pattern else None)

    __str__ = __repr__

class RouteGroup(Route):
    """ Route which represents a group of other routes

    Can have its own ``guards`` and a URL ``pattern``.

    Additional to :class:`.Route` params are:

    :param routes:
        a list of :class:`Route` objects
    """

    def __init__(self, routes, guards, pattern, url_pattern_cls=None,
            **annotations):
        super(RouteGroup, self).__init__(guards, pattern,
                url_pattern_cls=url_pattern_cls, **annotations)
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
                    idx[r.name] = (self.url_pattern_cls or URLPattern)('/')
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
            url += '?' + urlencode(kwargs)
        return url

    def match_pattern(self, path_info):
        """ Match ``path_info`` against route's ``pattern``"""
        if self.pattern is None:
            return path_info, ()
        return self.pattern.match(path_info)

    def match(self, path_info, request):
        path_info, args = self.match_pattern(path_info)
        guarded = []
        trace = Trace(args, {}, [self])
        trace = self.match_guards(request, trace)
        for subroute in self.routes:
            try:
                subtrace = subroute.match(path_info, request)
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
        return '%s(routes=%r, guards=%r, pattern=%r)' % (
            self.__class__.__name__, self.routes, self.guards, self.pattern)

    __str__ = __repr__

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
    for p in iter_entry_points('routr', name=name):
        r = p.load()
        if not isinstance(r, Route):
            raise RouteConfigurationError(
                "entry point '%s' doesn't point at Route instance" % p)
        routes.append(r)
    return RouteGroup(routes, [])

def route(*args, **kwargs):
    """ Directive for configuring routes in application

    :param args:
        ([method,] [pattern,] target) produces endpoint route
        ([method,] [pattern,] *routes) produces route group
    :param kwargs:
        name and guards are treated as name and guards for routes, other
        keyword args a are passed as annotations
    """

    def consume(pred):
        r = []
        while args:
            if not pred(args[0]):
                break
            r.append(args.pop(0))
        return r, args

    args = list(args)

    if not args:
        raise RouteConfigurationError('empty routes')

    method = args.pop(0) if isinstance(args[0], HTTPMethod) else GET
    name = kwargs.pop('name', None)
    url_pattern_cls = kwargs.pop('url_pattern_cls', None)

    if not args:
        raise RouteConfigurationError('empty routes')

    if len(args) == 1 and not isinstance(args[0], Route):
        target = args[0]
        return Endpoint(target, method, name, [], None,
                url_pattern_cls=url_pattern_cls, **kwargs)

    elif (
            len(args) == 2
            and isinstance(args[0], str)
            and not isinstance(args[1], Route)):
        pattern, target = args
        return Endpoint(target, method, name, [], pattern,
                url_pattern_cls=url_pattern_cls, **kwargs)

    else:
        if isinstance(args[0], str):
            pattern = args.pop(0)
        else:
            pattern = None

        guards, args = consume(
            lambda d: not isinstance(d, Route) and hasattr(d, '__call__'))

        routes, args = consume(
            lambda d: isinstance(d, Route))
        if routes:
            if url_pattern_cls:
                for r in routes:
                    if r.url_pattern_cls is None:
                        r.url_pattern_cls = url_pattern_cls
            return RouteGroup(routes, guards, pattern,
                    url_pattern_cls=url_pattern_cls, **kwargs)
        elif len(args) == 1:
            target = args[0]
            return Endpoint(target, method, name, guards,
                    pattern, url_pattern_cls=url_pattern_cls, **kwargs)
        elif not args and guards:
            target = guards.pop()
            return Endpoint(target, method, name, guards,
                    pattern, url_pattern_cls=url_pattern_cls, **kwargs)
        else:
            raise RouteConfigurationError(
                "improper usage of 'route' directive")
