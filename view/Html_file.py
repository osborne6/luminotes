import re
import cherrypy
from Tags import Html, Head, Title, Style, Meta, Body, H1, Div, Span, Hr, A


class Html_file( Html ):
  ENTRY_LINK_PATTERN = re.compile( u'<a\s+href="\/entries\/([a-z0-9]*)"\s*>', re.IGNORECASE )

  def __init__( self, notebook_name, entries ):
    relinked_entries = {} # map from entry id to relinked entry contents

    # relink all entry links so they point to named anchors within the page
    for entry in entries:
      contents = self.ENTRY_LINK_PATTERN.sub( r'<a href="#entry_\1">', entry.contents )
      relinked_entries[ entry.object_id ] = contents

    cherrypy.response.headerMap[ u"Content-Disposition" ] = u"attachment; filename=wiki.html"

    Html.__init__(
      self,
      Head(
        Style( file( u"static/css/download.css" ).read(), type = u"text/css" ),
        Meta( content = u"text/html; charset=UTF-8", http_equiv = u"content-type" ),
        Title( notebook_name ),
      ),
      Body(
        Div(
          H1( notebook_name ),
          [ Span(
            A( name = u"entry_%s" % entry.object_id ),
            Div(
              relinked_entries[ entry.object_id ],
              class_ = u"entry_frame",
            ),
          ) for entry in entries ],
          id = u"center_area",
        ),
      ),
      A( "Luminotes", href = "http://luminotes.com/" ),
    )
