"""

    routr.docparse -- generate routes from documentation
    ====================================================

"""

import re
import urlparse

from routr import HTTPMethod, route

__all__ = ("parse",)

_route_re = re.compile("""
    \s+
    (?P<method>(GET)|(POST)|(PUT)|(TRACE)|(DELETE)|(OPTIONS)|(HEAD)|(PATCH))
    \s+
    (?P<pattern>[^\?]+)
    (\?(?P<qs>[^\s]+))?
    \s+
    (?P<target>[a-zA-Z0-9\._]+)
    """, re.VERBOSE)

def parse(text):
    routes = []
    for line in text.split("\n"):
        if not line.strip():
            continue
        m = _route_re.match(line)
        if m:
            data = m.groupdict()
            routes.append(route(
                HTTPMethod(data["method"]),
                data["pattern"],
                data["target"]))
    return route(*routes)


