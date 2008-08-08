from Tags import Html, Head, Link, Meta, Body, P, Form, Span, Input


class Upload_page( Html ):
  def __init__( self, notebook_id, note_id, file_id, label_text, instructions_text ):
    Html.__init__(
      self,
      Head(
        Link( href = u"/static/css/upload.css", type = u"text/css", rel = u"stylesheet" ),
        Meta( content = u"text/html; charset=UTF-8", http_equiv = u"content-type" ),
      ),
      Body(
        Form(
          Span( u"%s: " % label_text, class_ = u"field_label" ),
          Input( type = u"hidden", id = u"notebook_id", name = u"notebook_id", value = notebook_id ),
          Input( type = u"hidden", id = u"note_id", name = u"note_id", value = note_id or u"" ),
          Input( type = u"file", id = u"upload", name = u"upload", class_ = "text_field", size = u"30" ),
          Input( type = u"submit", id = u"upload_button", class_ = u"button", value = u"upload" ),
          action = u"/files/upload?file_id=%s" % file_id,
          method = u"post",
          enctype = u"multipart/form-data",
        ),
        P( instructions_text ),
        Span( id = u"tick_preload" ),
        Input( type = u"hidden", id = u"file_id", value = file_id ),
      ),
    )
