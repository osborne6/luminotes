from Tags import Span, H3, P, A


class Thanks_note( Span ):
  def __init__( self, rate_plan_name ):
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
        You are now subscribed to Luminotes %s. Please click on one of your
        notebooks to the right to get started with your newly upgraded wiki.
        """ % rate_plan_name,
      ),
      P(
        u"""
        If you have any questions about your upgraded wiki or your Luminotes
        account, please
        """,
        A( u"contact support", href = u"/contact_info", target = "_top" ),
        u"""
        for assistance.
        """,
      ),
    )
