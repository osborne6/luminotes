from Tags import Form, Strong, Input


class Search_form( Form ):
  def __init__( self ):
    title = None

    Form.__init__(
      self,
      Strong( u"search: " ),
      Input( type = u"text", name = u"search_text", id = u"search_text", size = 30, maxlength = 512 ),
      id = u"search_form",
    )
