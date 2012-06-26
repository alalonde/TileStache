from string import Template
try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs
from StringIO import StringIO
import TileStache, Core

STANDARD_LAYER = 'standard'

def requestHandler(config, path_info, query_string):
    """ Generate a mime-type and response body for a given request.
    
        Requires a configuration and PATH_INFO (e.g. "/example/0/0/0.png").
        
        Config_hint parameter can be a path string for a JSON configuration file
        or a configuration object with 'cache', 'layers', and 'dirpath' properties.
        
        Query string is optional, currently used for JSON callbacks.
        
        Calls getTile() to render actual tiles, and getPreview() to render preview.html.
    """
    try:
        # ensure that path_info is at least a single "/"
        path_info = '/' + (path_info or '').lstrip('/')
        
        layer = config.layers[STANDARD_LAYER]
        query = parse_qs(query_string or '')
        try:
            callback = query['callback'][0]
        except KeyError:
            callback = None
        
        #
        # Special case for index page.
        #
        if path_info == '/':
            return getattr(layer.config, 'index', ('text/plain', 'TileStache says hello.'))

        coord, extension = TileStache.splitPathInfo(path_info)[1:]
        
        if path_info == '/':
            raise Exception(path_info)
        
        elif extension == 'html' and coord is None:
            mimetype, content = TileStache.getPreview(layer)

        elif extension.lower() in layer.redirects:
            other_extension = layer.redirects[extension.lower()]
            other_path_info = TileStache.mergePathInfo(layer.name(), coord, other_extension)
            raise Core.TheTileIsInAnotherCastle(other_path_info)
        
        else:
            mimetype, content = TileStache.getTile(layer, coord, extension)
    
        if callback and 'json' in mimetype:
            mimetype, content = 'application/javascript', '%s(%s)' % (callback, content)

    except Core.KnownUnknown, e:
        out = StringIO()
        
        print >> out, 'Known unknown!'
        print >> out, e
        print >> out, ''
        print >> out, '\n'.join(Core._rummy())
        
        mimetype, content = 'text/plain', out.getvalue()

    return mimetype, content

class WSGICustomTileServer (TileStache.WSGITileServer):
    """ WSGI Application that takes a dynamic layer and queries the database for only that layer.
        
        Inherits the constructor from TileStache WSGI, which just loads
        a TileStache configuration file into self.config.
    """
    def __call__(self, environ, start_response):
        """ Handle a request, using PATH_INFO and QUERY_STRING from environ.
        
            There are six required query string parameters: width, height,
            xmin, ymin, xmax and ymax. Layer name must be supplied in PATH_INFO.
        """
        if self.autoreload: # re-parse the config file on every request
            try:
                self.config = TileStache.parseConfigfile(self.config_path)
            except Exception, e:
                raise Core.KnownUnknown("Error loading Tilestache config file:\n%s" % str(e))

        try:
            layer, coord, ext = TileStache.splitPathInfo(environ['PATH_INFO'])
        except Core.KnownUnknown, e:
            return self._response(start_response, '400 Bad Request', str(e))

        try:
            query_params = self.config.layers[STANDARD_LAYER].provider.parameters
            t = Template(query_params['query'])
            query_params['query'] = t.substitute(map_slug=layer)
            mimetype, content = requestHandler(self.config, environ['PATH_INFO'], environ['QUERY_STRING'])
        
        except Core.TheTileIsInAnotherCastle, e:
            other_uri = environ['SCRIPT_NAME'] + e.path_info
            
            if environ['QUERY_STRING']:
                other_uri += '?' + environ['QUERY_STRING']
    
            start_response('302 Found', [('Location', other_uri), ('Content-Type', 'text/plain')])
            return ['You are being redirected to %s\n' % other_uri]
        
        request_layer = self.config.layers[STANDARD_LAYER]
        allowed_origin = request_layer.allowed_origin
        max_cache_age = request_layer.max_cache_age
        return self._response(start_response, '200 OK', str(content), mimetype, allowed_origin, max_cache_age)