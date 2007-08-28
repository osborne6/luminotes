from Tags import Div, H3, A


class Link_area( Div ):
  def __init__( self, notebook_id ):
    Div.__init__(
      self,
      Div(
        id = u"this_notebook_area",
      ),
      Div(
        id = u"notebooks_area",
      ),
    )
