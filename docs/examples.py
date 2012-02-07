# examples.py

from routr import route, POST, DELETE, PUT, HEAD

def welcome():
    """ welcome page"""
    pass

def list_news():
    """ list news"""

def api_list_news():
    """ API list news items"""

def api_create_news():
    """ API create news item"""

def api_get_news(id):
    """ API get news item by ``id``"""

routes = route(
    route(welcome),
    route("news", list_news),
    route("api",
        route("news", api_list_news),
        route(POST, "news", api_create_news),
        route("news/{int}", api_get_news)))
