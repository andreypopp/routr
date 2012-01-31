""" `routr` package

Example usage::

    from routr import route, schema
    from webob import exc
    from myapp.utils import AuthRequired, XHROnly, GeoBlocking

    routing = route(
        route("/", "myapp.views.index"),
        route("/news", "myapp.views.news"),
        route("/archive/{int:year}-{int:month}-{int:day}/", "myapp.views.arch"),
        route("/forecast/{int}-{int}-{int}/", "myapp.views.forecast"),
        route(
            "api",
            route(
                "/news",
                "myapp.views.api.news",
                schema.params(user_id=schema.Integer, limit=schema.Integer),
            route("myapp.views.api.comments", "/comments"),
            XHROnly),
        AuthRequired, GeoBlocking)

    adapter, view = routing(request, raise404=True)
    return adapter(view, request)

    router(
        "/news", "news_views",
        Params(limit=schema.Integer) + AuthRequired.user_id)

"""

__all__ = ("route", "NoMatchFound")

class NoMatchFound(Exception):
    """ No route was matched for request"""

def route(*directives):
    pass
