from Product_page import Product_page
from Tags import Div, Img, A, P, Span, I, Br


class Forums_page( Product_page ):
  def __init__( self, user, notebooks, first_notebook, login_url, logout_url, rate_plan, groups ):
    Product_page.__init__(
      self,
      user,
      first_notebook,
      login_url,
      logout_url,
      u"forums", # note title

      Div(
        Div(
          Img(
            src = u"/static/images/forums.png",
            width = u"335", height = u"47",
            alt = u"Discussion Forums",
          ),
        ),
        Div(
          Span( A( u"general discussion", href = u"/forums/general" ), class_ = u"forum_title" ),
          P(
            u"""
            Swap tips about making the most out of your personal wiki, and discuss your ideas for
            new Luminotes features and enhancements.
            """
          ),
          Span( A( u"technical support", href = u"/forums/support" ), class_ = u"forum_title" ),
          P( u"Having a problem with your wiki? Something not working as expected? Ask about it here." ),
          class_ = u"forums_text",
        ),
        class_ = u"forums_area", 
      ),

      Div(
        P(
          Span( u"Need more help?", class_ = u"hook_action_question" ), Br(),
          A( u"Contact support directly", href = u"/contact_info", class_ = u"hook_action" ),
          class_ = u"hook_action_area",
          separator = u"",
        ),
        class_ = u"center_area",
      ),
    )
