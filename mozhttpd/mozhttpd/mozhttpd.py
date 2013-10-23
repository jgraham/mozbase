"""Compatibility layer between wptserve and mozhttpd"""
import logging
import sys

from wptserve import server
from wptserve import handlers as wpthandlers
import moznetwork

class Request(object):
    def __init__(self, request):
        self.uri = request.url
        self.headers = request._raw_headers
        for key, value in request.url_parts._asdict().iteritems():
            setattr(self, key, value)
        self.body = request.body

class RequestHandler(object):
    def __init__(self, handler):
        self.handler = handler

    def __call__(self, request, response):
        status_code, headers, data = self.handler(Request(request), *request.route_match.groups())
        response.status = status_code
        response.headers.update((name, value) for name, value in headers.iteritems())
        response.content = data

        return response

class Handlers(object):
    def json_response(self, func):
        return wpthandlers.json_handler(func)

handlers = Handlers()

def urlhandlers_to_routes(urlhandlers):
    rv = []
    for handler in urlhandlers:
        method = handler["method"]
        path = handler["path"]
        func = handler["function"]
        if method == "DEL":
            method = "DELETE"
        rv.append((method, path, RequestHandler(func)))
    return rv

def MozHttpd(host="127.0.0.1", port=0, docroot=None,
             urlhandlers=None, proxy_host_dirs=False, log_requests=False):
    #TODO: proxy_host_dirs, log_requests
    routes = []

    logging.basicConfig()

    if urlhandlers is not None:
        routes.extend(urlhandlers_to_routes(urlhandlers))

    if docroot is not None:
        routes.append(("GET", ".*", wpthandlers.file_handler))

    return server.WebTestHttpd(host, port, doc_root=docroot, routes=routes)

def main(args=sys.argv[1:]):

    # parse command line options
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('-p', '--port', dest='port',
                      type="int", default=8888,
                      help="port to run the server on [DEFAULT: %default]")
    parser.add_option('-H', '--host', dest='host',
                      default='127.0.0.1',
                      help="host [DEFAULT: %default]")
    parser.add_option('-i', '--external-ip', action="store_true",
                      dest='external_ip', default=False,
                      help="find and use external ip for host")
    parser.add_option('-d', '--docroot', dest='docroot',
                      default=os.getcwd(),
                      help="directory to serve files from [DEFAULT: %default]")
    options, args = parser.parse_args(args)
    if args:
        parser.error("mozhttpd does not take any arguments")

    if options.external_ip:
        host = moznetwork.get_lan_ip()
    else:
        host = options.host

    # create the server
    server = MozHttpd(host=host, port=options.port, docroot=options.docroot)

    print "Serving '%s' at %s:%s" % (server.docroot, server.host, server.port)
    server.start(block=True)

if __name__ == '__main__':
    main()
