from Page import Page
from Tags import Div, H2, P, A, Img, Ul, Li


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
          u"Sorry, the page you are looking for couldn't be found. But not to worry. You've got a few options.",
          Ul(
            Li( u"Return to the", A( u"Luminotes personal wiki notebook", href = u"/" ), u"home page." ),
            Li( A( u"Contact support", href = u"mailto:%s" % support_email ), u"and report that the page you expected to find here is missing." ),
          ),
        ),
        class_ = u"error_box",
      ),
    )
