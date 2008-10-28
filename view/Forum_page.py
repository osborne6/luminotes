from Product_page import Product_page
from Tags import Div, H1, A, P


class Forum_page( Product_page ):
  def __init__( self, user, notebooks, first_notebook, login_url, logout_url, rate_plan, groups, forum_name, threads ):
    full_forum_name = "%s forum" % forum_name

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
        P(
          A( u"start a new discussion", href = u"/forums/%s/create_thread" % forum_name ),
          u" | ",
          A( u"all forums", href = u"/forums/" ),
          class_ = u"small_text",
        ),
        [ Div(
          A(
            thread.name,
            href = u"/forums/%s/%s" % ( forum_name, thread.object_id ),
          ),
        ) for thread in threads ],
        class_ = u"forum_threads", 
      ),
    )
