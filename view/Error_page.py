from Page import Page
from Tags import Div, H2, P, A, Ul, Li, Strong, Noscript, Img


class Error_page( Page ):
  def __init__( self, support_email, message = None ):
    header_image = Div(
      A( Img( src = "/static/images/luminotes_title.png" ), href = "/", title = "Luminotes personal wiki notebook" ),
      class_ = u"error_header",
    )

    if message:
      title = u"whoops"
      Page.__init__(
        self,
        title,
        header_image,
        Div(
          H2( title ),
          P( message ),
          class_ = u"error_box",
        ),
        include_js = False,
      )
      return

    title = u"uh oh"
    Page.__init__(
      self,
      title,
      header_image,
      Div(
        H2( title ),
        Noscript(
          P(
            Strong(
              u"""
              Please enable JavaScript in your web browser. JavaScript is necessary for many Luminotes
              features to work properly.
              """,
            ),
          ),
        ),
        P(
          u"Something went wrong! If you care, please",
          A( "let me know about it.", href = "mailto:%s" % support_email ),
          u"Be sure to include the following information:",
        ),
        Ul(
          Li( u"the series of steps you took to produce this error" ),
          Li( u"the time of the error" ),
          Li( u"the name of your web browser and its version" ),
          Li( u"any other information that you think is relevant" ),
        ),
        P(
          u"Thanks!",
        ),
        class_ = u"error_box",
      ),
      include_js = False,
    )
