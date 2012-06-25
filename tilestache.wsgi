import sys, os
stache_dir = '/mnt/Atlastory-staging/current/vendor/Tilestache'
sys.path.append(stache_dir)
import TileStache
application = TileStache.WSGITileServer(stache_dir + '/tilestache.cfg')
