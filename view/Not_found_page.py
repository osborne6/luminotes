from Page import Page
from Tags import Div, H2, P, A


class Not_found_page( Page ):
  def __init__( self ):
    title = u"404"

    Page.__init__(
      self,
      title,
      Div(
        H2( title ),
        P(
          u"This is not the page you're looking for. If you care, please",
          A( "let us know about it.", href = "/about/contact" ),
        ),
        P(
          u"Thanks!",
        ),
        class_ = u"box",
      ),
    )
