from routr import route
from routr.schema import Method

def view(id):
    """ Get data by ``id``"""
    pass

def news():
    """ Return news"""

def create_news():
    """ Create news item"""

def api_news():
    """ get news by JSON"""

routes = route(
    route("/{int}", view),
    route("news", news),
    route("news", create_news, [Method("POST")]),
    route("api",
        route("news", api_news)),
    )
