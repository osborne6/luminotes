import os.path
import cherrypy
from datetime import datetime
from Product_page import Product_page
from Page_navigation import Page_navigation
from Tags import Div, H1, A, P, Span, Link, Img


class Forum_page( Product_page ):
  def __init__(
    self, user, notebooks, first_notebook, login_url, logout_url, rate_plan, groups, forum_name,
    threads, total_thread_count, start = 0, count = None,
  ):
    base_path = cherrypy.request.path
    updates_path = "%s?rss" % base_path

    if forum_name == u"blog":
      full_forum_name = u"Luminotes %s" % forum_name
    else:
      full_forum_name = u"%s forum" % forum_name

    Product_page.__init__(
      self,
      user,
      first_notebook,
      login_url,
      logout_url,
      full_forum_name, # note title
      Link( rel = u"alternate", type = u"application/rss+xml", title = full_forum_name, href = updates_path ) or None,

      P(
        H1( full_forum_name ),
      ),
      Div(
        P(
          base_path.startswith( u"/forums/" ) and Span(
            A( u"start a new discussion", href = os.path.join( base_path, u"create_thread" ) ),
            u" | ",
            A( u"all forums", href = u"/forums/" ),
            u" | ",
          ) or None,
          A( u"subscribe to rss", href = updates_path ),
          A(
            Img( src = u"/static/images/rss.png", width = u"14", height = u"14", class_ = u"middle_image padding_left" ),
            href = updates_path,
          ),
          class_ = u"small_text",
        ) or None,
        [ Div(
          A(
            thread.name,
            href = ( forum_name == u"blog" ) and \
              os.path.join( base_path, thread.friendly_id ) or \
              "%s?posts=%s" % ( os.path.join( base_path, thread.object_id ), thread.note_count ),
          ),
          Span(
            self.post_count( thread, forum_name ),
            class_ = u"small_text",
          )
        ) for thread in threads ],
        class_ = u"forum_threads", 
      ),
      Page_navigation( base_path, len( threads ), total_thread_count, start, count ),
    )

  @staticmethod
  def post_count( thread, forum_name ):
    if forum_name != u"blog":
      if thread.note_count > 1:
        return u"(%s posts)" % thread.note_count
      return None

    if thread.note_count == 2:
      return u"(1 comment)"
    elif thread.note_count > 2:
      return u"(%s comments)" % ( thread.note_count - 1 )

    return None
