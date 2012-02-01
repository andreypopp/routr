""" Exceptions"""

from webob import exc

__all__ = (
    "NoMatchFound", "RouteNotFound", "RouteGuarded",
    "RouteConfigurationError", "InvalidRoutePattern")

class NoMatchFound(Exception):

    response = NotImplemented

class RouteNotFound(NoMatchFound):
    """ No route was matched for request"""

    response = exc.HTTPNotFound()

class RouteGuarded(NoMatchFound):
    """ There was matched routes but they were guarded

    :param response:
        underlying response from guard, usually it's instance of
        :class:``webob.exc.HTTPException``
    """

    def __init__(self, response):
        self.response = response

class RouteConfigurationError(Exception):
    """ Improperly configured routes"""

class InvalidRoutePattern(RouteConfigurationError):
    """ Invalid route pattern"""
