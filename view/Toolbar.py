from Tags import Div, Ul, Li, A, Input


class Toolbar( Div ):
  def __init__( self ):
    Div.__init__(
      self,
      Ul(
        Li( Input( type = u"button", value = u"+", id = u"newNote", title = u"new note [ctrl-N]", class_ = u"button" ) ),
        Li( Input( type = u"button", value = u"&#8594", id = u"createLink", title = u"note link [ctrl-L]", class_ = u"button" ) ),
      ),
      Ul(
        Li( Input( type = u"button", value = u"B", id = u"bold", title = u"bold [ctrl-B]", class_ = u"button" ) ),
        Li( Input( type = u"button", value = u"I", id = u"italic", title = u"italic [ctrl-I]", class_ = u"button" ) ),
        Li( Input( type = u"button", value = u"U", id = u"underline", title = u"underline [ctrl-U]", class_ = u"button" ) ),
        Li( Input( type = u"button", value = u"T", id = u"title", title = u"title [ctrl-T]", class_ = u"button" ) ),
      ),
      Ul(
        Li( Input( type = u"button", value = u"&#149;", id = u"insertUnorderedList", title = u"bullet list [ctrl-period]", class_ = u"button" ) ),
        Li( Input( type = u"button", value = u"1.", id = u"insertOrderedList", title = u"numbered list [ctrl-1]", class_ = u"button" ) ),
      ),
      id = u"toolbar",
      class_ = u"undisplayed", # start out as hidden, and then shown in the browser if the current notebook is read-write
    )
