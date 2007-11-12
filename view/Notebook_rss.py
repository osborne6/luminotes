import cgi
from Rss_channel import Rss_channel
from Rss_item import Rss_item


class Notebook_rss( Rss_channel ):
  def __init__(
    self,
    user,
    rate_plan,
    notebooks,
    notebook,
    parent_id = None,
    login_url = None,
    logout_url = None,
    startup_notes = None,
    total_notes_count = None,
    notes = None,
    note_read_write = True,
    start = None,
    count = None,
    http_url = u"",
    conversion = None,
  ):
    if notebook.name == u"Luminotes":
      notebook_path = u"/"
    elif notebook.name == u"Luminotes user guide":
      notebook_path = u"/guide"
    elif notebook.name == u"Luminotes blog":
      notebook_path = u"/blog"
    else:
      notebook_path = u"/notebooks/%s" % notebook.object_id

    notebook_path = http_url + notebook_path

    Rss_channel.__init__(
      self,
      notebook.name,
      notebook_path,
      notebook.name,
      [ Rss_item(
        title = cgi.escape( note.title ),
        link = u"%s?note_id=%s" % ( notebook_path, note.object_id ),
        description = cgi.escape( note.contents ),
        date = note.creation.strftime( "%Y-%m-%dT%H:%M:%SZ" ),
        guid = u"%s?note_id=%s" % ( notebook_path, note.object_id ),
      ) for note in notes ],
    )
