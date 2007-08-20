from Page import Page
from Tags import Div, H2, P, A, Ul, Li, Strong


class Error_page( Page ):
  def __init__( self, support_email ):
    title = u"uh oh"

    Page.__init__(
      self,
      title,
      Div(
        H2( title ),
        P(
          u"Something went wrong! If you care, please",
          A( "let us know about it.", href = "mailto:%s" % support_email ),
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
        P(
          Strong( u"P.S." ),
          u"""
          If Javascript isn't enabled in your browser, please enable it.
          """,
        ),
        class_ = u"error_box",
      ),
    )
