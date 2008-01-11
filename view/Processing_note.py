from Tags import Html, Head, Meta, H3, P


class Processing_note( Html ):
  def __init__( self, rate_plan, retry_count ):
    if not retry_count:
      retry_count = 0

    retry_count += 1

    Html.__init__(
      self,
      Head(
        Meta(
          http_equiv = u"Refresh",
          content = u"2; URL=/users/thanks?item_number=%s&retry_count=%s" % ( rate_plan, retry_count ),
        ),
      ),
      H3( u"processing..." ),
      P(
        """
        Your subscription is being processed. This shouldn't take more than a minute. Please wait...
        """,
      ),
    )
