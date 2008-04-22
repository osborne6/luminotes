import cgi
from urllib import urlencode
from Rss_channel import Rss_channel
from Rss_item import Rss_item


class Updates_rss( Rss_channel ):
  def __init__(
    self,
    recent_notes,
    notebook_id,
    notebook_name,
    https_url,
  ):
    if notebook_name == u"Luminotes":
      notebook_path = u"/"
    elif notebook_name == u"Luminotes user guide":
      notebook_path = u"/guide"
    elif notebook_name == u"Luminotes blog":
      notebook_path = u"/blog"
    else:
      notebook_path = u"/notebooks/%s" % notebook_id

    notebook_path = https_url + notebook_path

    Rss_channel.__init__(
      self,
      cgi.escape( notebook_name ),
      notebook_path,
      u"Luminotes notebook",
      [ Rss_item(
        title = u"Note updated",
        link = self.note_link( notebook_id, notebook_name, note_id, revision, https_url ),
        description = cgi.escape( u'A note in <a href="%s">this notebook</a> has been updated. <a href="%s?note_id=%s">View the note.</a>' % ( notebook_path, notebook_path, note_id ) ),
        date = revision.strftime( "%Y-%m-%dT%H:%M:%SZ" ),
        guid = self.note_link( notebook_id, notebook_name, note_id, revision, https_url ),
      ) for ( note_id, revision ) in recent_notes ],
    )

  @staticmethod
  def note_link( notebook_id, notebook_name, note_id, revision, https_url ):
    query = urlencode( [
      ( u"notebook_id", notebook_id ),
      ( u"notebook_name", notebook_name ),
      ( u"note_id", note_id ),
      ( u"revision", unicode( revision ) ),
    ] )

    return cgi.escape( u"%s/notebooks/get_update_link?%s" % ( https_url, query ) )
