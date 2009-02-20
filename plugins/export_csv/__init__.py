import re
import csv
from cStringIO import StringIO
from model.User import User


FILE_LINK_PATTERN = re.compile( u'<a\s+href="[^"]*\/files\/download\?file_id=[^"]+"[^>]*>', re.IGNORECASE )
IMAGE_PATTERN = re.compile( u'<img [^>]* ?/?>', re.IGNORECASE )
NEWLINE_PATTERN = re.compile( u'[\r\n]+' )


def export( database, notebook, notes, response_headers ):
  """
  Format the given notes as a CSV file and return it as a streaming generator.
  """
  buffer = StringIO()
  writer = csv.writer( buffer, quoting = csv.QUOTE_NONNUMERIC )

  response_headers[ u"Content-Disposition" ] = u"attachment; filename=%s.csv" % notebook.friendly_id
  response_headers[ u"Content-Type" ] = u"text/csv;charset=utf-8"

  def prepare_contents( contents ):
    contents = FILE_LINK_PATTERN.sub( '<a>', contents )
    contents = IMAGE_PATTERN.sub( '', contents )
    contents = NEWLINE_PATTERN.sub( ' ', contents )
    return contents.strip()

  def stream():
    writer.writerow( ( u"contents", u"title", u"note_id", u"startup", u"username", u"revision_date" ) )
    yield buffer.getvalue()
    buffer.truncate( 0 )

    for note in notes:
      user = None
      if note.user_id:
        user = database.load( User, note.user_id )

      writer.writerow( (
        note.contents and prepare_contents( note.contents ).encode( "utf8" ) or None,
        note.title and note.title.strip().encode( "utf8" ) or None,
        note.object_id,
        note.startup and 1 or 0,
        note.user_id and user and user.username and user.username.encode( "utf8" ) or u"",
        note.revision,
      ) )

      yield buffer.getvalue()
      buffer.truncate( 0 )

  return stream()
