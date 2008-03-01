from Page import Page
from Tags import Div, H2, P, A, Img


class Not_found_page( Page ):
  def __init__( self, support_email ):
    title = u"404"
    header_image = Div(
      A( Img( src = u"/static/images/luminotes_title_full.png", width = u"206", height = u"69" ), href = u"/", alt = u"Luminotes personal wiki notebook" ),
      class_ = u"error_header",
    )

    Page.__init__(
      self,
      title,
      header_image,
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
    )
