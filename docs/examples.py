# examples.py

from routr import route, POST, GET

def api_list_news():
    """ API list news items"""

def api_create_news():
    """ API create news item"""

def api_get_news(id):
    """ API get news item by ``id``"""

routes = route(
    route("api",
        route(GET, "news", api_list_news),
        route(POST, "news", api_create_news),
        route(GET, "news/{int}", api_get_news)))
