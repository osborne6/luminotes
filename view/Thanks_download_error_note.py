from Tags import Span, H3, P, A


class Thanks_download_error_note( Span ):
  def __init__( self ):
    Span.__init__(
      self,
      H3( u"thank you" ),
      P(
        u"""
        Thank you for purchasing Luminotes Desktop!
        """,
      ),
      P(
        u"""
        Luminotes has not yet received confirmation of your payment. Please
        check back in a few minutes by refreshing this page, or check your
        email for a Luminotes Desktop download message.
        """
      ),
      P(
        """
        If your payment is not received within the next few minutes, please
        """,
        A( u"contact support", href = u"/contact_info", target = "_top" ),
        u"""
        for assistance.
        """,
      ),
    )
