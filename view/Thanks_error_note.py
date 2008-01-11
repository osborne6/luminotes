from Tags import Span, H3, P, A


class Thanks_error_note( Span ):
  def __init__( self ):
    Span.__init__(
      self,
      H3( u"thank you" ),
      P(
        u"""
        Thank you for upgrading your Luminotes account!
        """,
      ),
      P(
        u"""
        Luminotes has not yet received confirmation of your subscription. If your
        account is not automatically upgraded within the next few minutes, please
        """,
        A( u"contact support", href = u"/contact_info", target = "_top" ),
        u"""
        for assistance.
        """,
      ),
      P(
        u"""
        Note: You can check the current status of your account by refreshing the
        """,
        A( u"upgrade", href = u"/upgrade", target = "_top" ),
        u"""
        page while logged in.
        """
      ),
    )
