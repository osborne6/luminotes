from Tags import Html, Head, Link, Script, Meta, Body


class Entry_page( Html ):
  def __init__( self, id ):
    Html.__init__(
      self,
      Head(
        Link( rel = u"stylesheet", type = u"text/css", href = u"/static/css/entry.css" ),
        Script( type = u"text/javascript", src = u"/static/js/MochiKit.js" ),
        Script( type = u"text/javascript", src = u"/static/js/Invoker.js" ),
        Meta( content = u"text/html; charset=UTF-8", http_equiv = u"content-type" ),
      ),
      Body(
        onload = u"parent.editor_loaded( '%s' );" % id,
      ),
    )
