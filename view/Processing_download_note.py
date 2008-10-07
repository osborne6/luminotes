from Tags import Html, Head, Meta, H3, P


class Processing_download_note( Html ):
  def __init__( self, access_id = None, tx = None, retry_count = None ):
    if not retry_count:
      retry_count = 0

    retry_count += 1

    if tx:
      meta_content = u"2; URL=/users/thanks_download?tx=%s&retry_count=%s" % ( tx, retry_count )
    elif access_id:
      meta_content = u"2; URL=/users/thanks_download?access_id=%s&retry_count=%s" % ( access_id, retry_count )
    else:
      raise Exception( u"either tx or access_id required" ) 

    Html.__init__(
      self,
      Head(
        Meta(
          http_equiv = u"Refresh",
          content = meta_content,
        ),
      ),
      H3( u"processing..." ),
      P(
        """
        Your payment is being processed. This shouldn't take more than a minute. Please wait...
        """,
      ),
    )
