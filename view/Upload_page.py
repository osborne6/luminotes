from Tags import Html, Head, Link, Meta, Body, P, Form, Span, Input


class Upload_page( Html ):
  def __init__( self, notebook_id, note_id ):
    Html.__init__(
      self,
      Head(
        Link( href = u"/static/css/upload.css", type = u"text/css", rel = u"stylesheet" ),
        Meta( content = u"text/html; charset=UTF-8", http_equiv = u"content-type" ),
      ),
      Body(
        Form(
          Span( u"attach file: ", class_ = u"field_label" ),
          Input( type = u"file", id = u"file", name = u"file", class_ = "text_field", size = u"30" ),
          Input( type = u"submit", id = u"upload_button", class_ = u"button", value = u"upload" ),
          Input( type = u"hidden", id = u"notebook_id", name = u"notebook_id", value = notebook_id ),
          Input( type = u"hidden", id = u"note_id", name = u"note_id", value = note_id ),
          action = u"/files/upload_file",
          method = u"post",
          enctype = u"multipart/form-data",
        ),
        P( u"Please select a file to upload." ),
        Span( id = u"tick_preload" ),
      ),
    )
