import re
import cherrypy
from view.Tags import Html, Head, Title, Style, Meta, Body, H1, Div, Span, Hr, A


class Html_file( Html ):
  NOTE_LINK_PATTERN = re.compile( u'<a\s+href="[^"]*(?:\/notebooks\/)?[^>]+[?&]note_id=([a-z0-9]*)"[^>]*>', re.IGNORECASE )
  IMAGE_PATTERN = re.compile( u'<img [^>]* ?/?>', re.IGNORECASE )

  def __init__( self, notebook, notes ):
    relinked_notes = {} # map from note id to relinked note contents

    # relink all note links so they point to named anchors within the page. also, for now, remove all
    # images since they're not presently included with the download
    for note in notes:
      contents = self.NOTE_LINK_PATTERN.sub( r'<a href="#note_\1">', note.contents )
      contents = self.IMAGE_PATTERN.sub( '', contents )
      relinked_notes[ note.object_id ] = contents

    cherrypy.response.headerMap[ u"Content-Disposition" ] = u"attachment; filename=%s.html" % notebook.friendly_id

    Html.__init__(
      self,
      Head(
        Style( file( u"static/css/download.css" ).read(), type = u"text/css" ),
        Meta( content = u"text/html; charset=UTF-8", http_equiv = u"content-type" ),
        Title( notebook.name ),
      ),
      Body(
        Div(
          H1( notebook.name ),
          [ Span(
            A( name = u"note_%s" % note.object_id ),
            Div(
              relinked_notes[ note.object_id ],
              class_ = u"note_frame",
            ),
          ) for note in notes ],
          A( "Luminotes", href = "http://luminotes.com/" ),
          id = u"center_area",
        ),
      ),
    )
