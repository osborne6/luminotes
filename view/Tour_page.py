from Product_page import Product_page
from Tags import Div, H1, Img, A, Ol, Li, P, Span, I, Br


class Tour_page( Product_page ):
  def __init__( self, user, notebooks, first_notebook, login_url, logout_url, rate_plan ):
    Product_page.__init__(
      self,
      user,
      first_notebook,
      login_url,
      logout_url,
      u"tour", # note title

      Div(
        H1(
          Img(
            src = u"/static/images/tour.png",
            width = u"277", height = u"47",
            alt = u"Luminotes tour",
          ),
        ),
        Div(
          Img( src = u"/static/images/tour_screenshot1.png", width = u"725", height = u"560", class_ = u"tour_screenshot" ),
          Div(
            Div(
              Ol(
                Li( u"Format your wiki with this convenient toolbar" ),
                Li( u"Just start typing &mdash; everything is saved automatically" ),
                Li( u"Search through your entire wiki" ),
                Li( u"Make as many notebooks as you want" ),
                class_ = u"tour_list",
              ),
              class_ = u"tour_text",
            ),
          ),
        ),
        Div(
          Img( src = u"/static/images/tour_screenshot2.png", width = u"725", height = u"558", class_ = u"tour_screenshot" ),
          Div(
            Div(
              Ol(
                Li( u"Connect your thoughts with links between notes" ),
                Li( u"Track past revisions and make updates without worry" ),
                Li( u"Download your complete wiki with a single click" ),
                Li( u"Attach files to your wiki and download them anytime" ),
                class_ = u"tour_list",
              ),
              class_ = u"tour_text",
            ),
          ),
        ),
        Div(
          Img( src = u"/static/images/tour_screenshot3.png", width = u"725", height = u"558", class_ = u"tour_screenshot" ),
          Div(
            Div(
              Ol(
                Li( u"Share your wiki with friends and colleagues" ),
                Li( u"Send invites simply by entering email addresses" ),
                Li( u"Control how much access each person gets" ),
                Li( u"Revoke access at any time" ),
                class_ = u"tour_list",
              ),
              class_ = u"tour_text",
            ),
          ),
          class_ = u"tour_screenshot_wrapper",
        ),
        class_ = u"tour_area" 
      ),

      Div(
        P(
          Span( u"Like what you've seen so far?", class_ = u"hook_action_question" ), Br(),
          A( u"Try the demo", href = u"/users/demo", class_ = u"hook_action" ),
          Span( u" or ", class_ = u"hook_action_or" ),
          A( u"Sign up", href = u"/pricing", class_ = u"hook_action"  ),
          class_ = u"hook_action_area",
          separator = u"",
        ),
        class_ = u"center_area",
      ),
    )
