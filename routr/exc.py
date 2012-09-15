"""

    routr.exc -- exceptions
    =======================

"""

from webob import exc

__all__ = (
    'NoMatchFound', 'NoURLPatternMatched', 'RouteGuarded', 'MethodNotAllowed',
    'RouteConfigurationError', 'InvalidRoutePattern',
    'RouteReversalError')

class NoMatchFound(Exception):
    """ Raised when request wasn't matched against any route

    :attr response:
        :class:`webob.Response` object to return to client
    """

    response = NotImplemented

class NoURLPatternMatched(NoMatchFound):
    """ Raised when request wasn't matched against any URL pattern"""

    response = exc.HTTPNotFound()

class RouteGuarded(NoMatchFound):
    """ Raised when request was matched against URL pattern of one or more
    routes but was guarded

    :param response:
        underlying response from guard, usually it's instance of
        :class:``webob.exc.HTTPException``
    """

    def __init__(self, reason, response):
        self.reason = reason
        self.response = response

class MethodNotAllowed(NoMatchFound):
    """ Raised when request was matched but request method isn't allowed"""

    response = exc.HTTPMethodNotAllowed()

class RouteConfigurationError(Exception):
    """ Routes were configured improperly

    Errors of such type can be only raised during initial configuration and not
    during runtime.
    """

class InvalidRoutePattern(RouteConfigurationError):
    """ Route configured with invalid route pattern"""

class RouteReversalError(Exception):
    """ Cannot reverse route"""
