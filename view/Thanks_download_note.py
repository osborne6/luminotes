from Tags import Span, H3, P, A
from config.Version import VERSION


class Thanks_download_note( Span ):
  def __init__( self, download_url ):
    news_url = u"http://luminotes.com/hg/luminotes/file/%s/NEWS" % VERSION

    Span.__init__(
      self,
      H3( u"thank you" ),
      P(
        u"""
        Thank you for purchasing Luminotes Desktop! Your payment has been received,
        and a receipt for your purchase has been emailed to you.
        """,
      ),
      P(
        A( u"Download Luminotes Desktop version %s" % VERSION, href = download_url ),
      ),
      P(
        A( "What's new in this release", href = news_url, target = "_new" ),
        class_ = u"small_text",
      ),
      P(
        u"""
        It's a good idea to bookmark this page so that you can download
        Luminotes Desktop or upgrade to new versions as they are released.
        """,
      ),
      P(
        u"""
        If you have any questions about Luminotes Desktop or your purchase, please
        """,
        A( u"contact support", href = u"/contact_info", target = "_top" ),
        u"""
        for assistance.
        """,
      ),
    )
