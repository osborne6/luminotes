from Tags import Form, Input


class Search_form( Form ):
  def __init__( self ):
    title = None

    Form.__init__(
      self,
      Input( type = u"text", name = u"search_text", id = u"search_text", maxlength = 512, value = "search" ),
      id = u"search_form",
    )
