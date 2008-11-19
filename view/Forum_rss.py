import cgi
import os.path
import cherrypy
from Rss_channel import Rss_channel
from Rss_item import Rss_item


class Forum_rss( Rss_channel ):
  def __init__(
    self,
    user,
    notebooks,
    first_notebook,
    login_url,
    logout_url,
    rate_plan,
    groups,
    forum_name,
    threads,
    total_thread_count,
    start = 0,
    count = None,
  ):
    forum_path = cherrypy.request.base + cherrypy.request.path
    if forum_name == u"blog":
      full_forum_name = u"Luminotes %s" % forum_name
    else:
      full_forum_name = u"%s forum" % forum_name

    Rss_channel.__init__(
      self,
      full_forum_name,
      forum_path,
      full_forum_name,
      [ Rss_item(
        title = cgi.escape( thread.name ),
        link = os.path.join( forum_path, ( forum_name == u"blog" ) and thread.friendly_id or thread.object_id ),
        description = cgi.escape( thread.name ),
        date = thread.revision.strftime( "%Y-%m-%dT%H:%M:%SZ" ),
        guid = os.path.join( forum_path, ( forum_name == u"blog" ) and thread.friendly_id or thread.object_id ),
      ) for thread in threads ],
    )
