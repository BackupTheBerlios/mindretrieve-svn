import archive_view
import _control
import docreader
import help
import home
import snoop
import history
import updateParent
import weblib
import weblibImport
import weblibMultiForm
import weblibTagCategorize

# list of tuple of (script_name, module)
cgi_registry = [
  ('/___'                  , _control),
  ('/archive_view'         , archive_view),
  ('/docreader'            , docreader),
  ('/help'                 , help),
  ('/history'              , history),
  ('/search'               , history),  # for compatibility to version 0.4?
  ('/snoop'                , snoop),
  ('/updateParent'         , updateParent),
  ('/weblib/import'        , weblibImport),
  ('/weblib/multiform'     , weblibMultiForm),
  ('/weblib/tag_categorize', weblibTagCategorize),
  ('/weblib'               , weblib),
  ('/'                     , weblib),
]


