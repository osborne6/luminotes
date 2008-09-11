from Tags import Html, Head, Meta, H3, P


class Processing_download_note( Html ):
  def __init__( self, download_access_id, retry_count ):
    if not retry_count:
      retry_count = 0

    retry_count += 1

    Html.__init__(
      self,
      Head(
        Meta(
          http_equiv = u"Refresh",
          content = u"2; URL=/users/thanks_download?access_id=%s&retry_count=%s" %
                    ( download_access_id, retry_count ),
        ),
      ),
      H3( u"processing..." ),
      P(
        """
        Your payment is being processed. This shouldn't take more than a minute. Please wait...
        """,
      ),
    )
