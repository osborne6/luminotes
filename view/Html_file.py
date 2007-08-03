import re
import cherrypy
from Tags import Html, Head, Title, Style, Meta, Body, H1, Div, Span, Hr, A


class Html_file( Html ):
  NOTE_LINK_PATTERN = re.compile( u'<a\s+href="\/notebooks\/[a-z0-9]*\?note_id=([a-z0-9]*)"[^>]*>', re.IGNORECASE )

  def __init__( self, notebook_name, notes ):
    relinked_notes = {} # map from note id to relinked note contents

    # relink all note links so they point to named anchors within the page
    for note in notes:
      contents = self.NOTE_LINK_PATTERN.sub( r'<a href="#note_\1">', note.contents )
      relinked_notes[ note.object_id ] = contents

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
            A( name = u"note_%s" % note.object_id ),
            Div(
              relinked_notes[ note.object_id ],
              class_ = u"note_frame",
            ),
          ) for note in notes ],
          id = u"center_area",
        ),
      ),
      A( "Luminotes", href = "http://luminotes.com/" ),
    )
