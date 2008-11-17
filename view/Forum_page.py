import os.path
import cherrypy
from Product_page import Product_page
from Page_navigation import Page_navigation
from Tags import Div, H1, A, P


class Forum_page( Product_page ):
  def __init__(
    self, user, notebooks, first_notebook, login_url, logout_url, rate_plan, groups, forum_name,
    threads, total_thread_count, start = 0, count = None,
  ):
    base_path = cherrypy.request.path

    if base_path.startswith( u"/forums/" ):
      full_forum_name = u"%s forum" % forum_name
    else:
      full_forum_name = u"Luminotes %s" % forum_name

    Product_page.__init__(
      self,
      user,
      first_notebook,
      login_url,
      logout_url,
      full_forum_name, # note title

      P(
        H1( full_forum_name ),
      ),
      Div(
        base_path.startswith( u"/forums/" ) and P(
          A( u"start a new discussion", href = os.path.join( base_path, u"create_thread" ) ),
          u" | ",
          A( u"all forums", href = u"/forums/" ),
          class_ = u"small_text",
        ) or None,
        [ Div(
          A(
            thread.name,
            href = os.path.join( base_path, thread.object_id ),
          ),
        ) for thread in threads ],
        class_ = u"forum_threads", 
      ),
      Page_navigation( base_path, len( threads ), total_thread_count, start, count ),
    )
