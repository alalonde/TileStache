import sys, os
stache_dir = '/mnt/Atlastory-staging/current/vendor/Tilestache'
sys.path.append(stache_dir)
from TileStache.WSGICustomTileServer import WSGICustomTileServer
application = WSGICustomTileServer(stache_dir + '/tilestache.cfg')
