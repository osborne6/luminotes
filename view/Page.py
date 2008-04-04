from Tags import Html, Head, Link, Script, Meta, Title, Body, Div, A, H1


class Page( Html ):
  def __init__( self, title, *children, **attrs ):
    head_types = ( Link, Script, Meta )   # node types to move to the Head section
    app_name = u"Luminotes"
    if not title: title = u"personal wiki notebook"

    if "id" not in attrs:
      attrs[ "id" ] = u"content"

    # move certain types of children from the body to the head
    Html.__init__(
      self,
      Head(
        Link( rel = u"stylesheet", type = u"text/css", href = u"/static/css/style.css" ),
        Script( type = u"text/javascript", src = u"https://ssl.google-analytics.com/urchin.js" ) or None,
        Meta( content = u"text/html; charset=UTF-8", http_equiv = u"content-type" ),
        [ child for child in children if type( child ) in head_types ],
        Title( title and u"%s: %s" % ( app_name, title ) or app_name ),
        """<!--[if IE 6]><link href="/static/css/ie6.css" type="text/css" rel="stylesheet"></link><![endif]-->""",
        """<!--[if IE 7]><link href="/static/css/ie7.css" type="text/css" rel="stylesheet"></link><![endif]-->""",
      ),
      Body(
        Div(
          *[ child for child in children if type( child ) not in head_types ],
          **attrs
        ),
      ),
      id = "html",
      xmlns = u"http://www.w3.org/1999/xhtml",
      prefix = u'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">\n'
    )
