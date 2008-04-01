from Tags import Html, Head, Title, Body, Img, Div, A


class File_preview_page( Html ):
  def __init__( self, file_id, filename, quote_filename ):
    Html.__init__(
      self,
      Head(
        Title( filename ),
      ),
      Body(
        A(
          Img( src = u"/files/image?file_id=%s" % file_id, style = "border: 0;" ),
          href = u"/files/download?file_id=%s&quote_filename=%s&preview=False" % ( file_id, quote_filename ),
        ),
        Div(
          A(
            u"download %s" % filename,
            href = u"/files/download?file_id=%s&quote_filename=%s&preview=False" % ( file_id, quote_filename ),
          ),
        ),
      ),
    )
