from string import Template
try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs
from StringIO import StringIO
import TileStache, Core

class WSGICustomTileServer (TileStache.WSGITileServer):
    """ WSGI Application that takes a dynamic layer and queries the database for only that layer.
        
        Inherits the constructor from TileStache WSGI, which just loads
        a TileStache configuration file into self.config.
        
        TODO: test with multiple requests, as it depends on a single version of the configuration file
        that is modified on every request.
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
            config_val = self.config.layers.popitem()
            self.config.layers[layer] = config_val[1]
            query_params = self.config.layers[layer].provider.parameters
            t = Template(query_params['query'])
            query_params['query'] = t.substitute(map_slug=layer)
            mimetype, content = TileStache.requestHandler(self.config, environ['PATH_INFO'], environ['QUERY_STRING'])
        
        except Core.TheTileIsInAnotherCastle, e:
            other_uri = environ['SCRIPT_NAME'] + e.path_info
            
            if environ['QUERY_STRING']:
                other_uri += '?' + environ['QUERY_STRING']
    
            start_response('302 Found', [('Location', other_uri), ('Content-Type', 'text/plain')])
            return ['You are being redirected to %s\n' % other_uri]
        
        request_layer = self.config.layers[layer]
        allowed_origin = request_layer.allowed_origin
        max_cache_age = request_layer.max_cache_age
        return self._response(start_response, '200 OK', str(content), mimetype, allowed_origin, max_cache_age)