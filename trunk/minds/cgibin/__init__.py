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
import history
import updateParent
import weblib
import weblibImport
import weblibMultiForm
import weblibTagCategorize

# list of tuple of (script_name, module)
cgi_registry = [
  ('/_config'              , _config),
  ('/_threadpool'          , _threadpool),
  ('/archive_view'         , archive_view),
  ('/config'               , config),
  ('/docreader'            , docreader),
  ('/help'                 , help),
  ('/home'                 , home),
  ('/indexnow'             , indexnow),
  ('/library'              , library),
  ('/search'               , search),
  ('/snoop'                , snoop),
  ('/history'              , history),
  ('/updateParent'         , updateParent),
  ('/weblib/import'        , weblibImport),
  ('/weblib/multiform'     , weblibMultiForm),
  ('/weblib/tag_categorize', weblibTagCategorize),
  ('/weblib'               , weblib),
  ('/'                     , home),
]


