from Page import Page
from Tags import Div, H2, P, A


class Not_found_page( Page ):
  def __init__( self, support_email ):
    title = u"404"

    Page.__init__(
      self,
      title,
      Div(
        H2( title ),
        P(
          u"This is not the page you're looking for. If you care, please",
          A( "let me know about it.", href = "mailto:%s" % support_email ),
        ),
        P(
          u"Thanks!",
        ),
        class_ = u"error_box",
      ),
      include_js = False,
    )
