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
        [ Div(
          A(
            thread.name,
            href = u"/forums/threads/%s" % thread.object_id,
          ),
        ) for thread in threads ],
        class_ = u"forums_text", 
      ),
    )
