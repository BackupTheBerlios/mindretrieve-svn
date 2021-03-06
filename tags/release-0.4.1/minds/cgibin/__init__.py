import _config
import _threadpool
import archive_view
import config
import docreader
import help
import home
import indexnow
import library
import search
import snoop

cgi_registry = {
  ''             : home,
  '_config'      : _config,
  '_threadpool'  : _threadpool,
  'archive_view' : archive_view,
  'config'       : config,
  'docreader'    : docreader,
  'help'         : help,
  'home'         : home,
  'indexnow'     : indexnow,
  'library'      : library,
  'search'       : search,
  'snoop'        : snoop,
}
