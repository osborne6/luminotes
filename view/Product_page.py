from Page import Page
from Tags import Link, Div, Img, A, Span


class Product_page( Page ):
  def __init__( self, user, first_notebook, login_url, logout_url, *nodes ):
    Page.__init__(
      self,
      None, # use the default title
      Link( rel = u"stylesheet", type = u"text/css", href = u"/static/css/product.css" ),

      Div(
        Div(
          Img(
            src ="/static/images/luminotes_title.png",
            class_ = u"luminotes_title", width = u"193", height = u"60",
            alt = u"Luminotes",
          ),
          ( login_url and user.username == u"anonymous" ) and Div(
            A( u"sign up", href = u"/sign_up", class_ = u"bold_link" ), u" | ",
            A(
              u"login",
              href = login_url,
              id = u"login_link",
              class_ = u"bold_link",
            ),
            class_ = u"header_user_links",
          ) or Div(
            u"logged in as %s" % ( user.username or u"a guest" ),
            u" | ",
            first_notebook and Span(
              A(
                u"my wiki",
                href = u"/notebooks/%s" % first_notebook.object_id,
              ),
              u" | ",
            ) or None,
            user.username and Span(
              A(
                u"upgrade",
                href = u"/upgrade",
                title = u"Upgrade your Luminotes account.",
                class_ = u"bold_link",
              ),
              " | ",
            ) or Span(
              A(
                u"sign up",
                href = u"/sign_up",
                title = u"Sign up for a real Luminotes account.",
              ),
              " | ",
            ) or None,
            A(
              u"logout",
              href = logout_url,
              id = u"logout_link",
              title = u"Sign out of your account.",
            ),
            class_ = u"header_user_links",
          ),
          Div(
            Span( u"home", class_ = u"bold_link" ), u" | ",
            A( u"tour", href = u"/take_a_tour" ), u" | ",
            A( u"demo", href = u"/users/demo" ), u" | ",
            A( u"pricing", href = u"/upgrade" ), u" | ",
            A( u"faq", href = u"/faq" ), u" | ",
            A( u"help", href = u"/guide" ), u" | ",
            A( u"contact", href = u"/contact_info" ), u" | ",
            A( u"team", href = u"/meet_the_team" ), u" | ",
            A( u"blog", href = u"/blog" ), u" | ",
            A( u"privacy", href = u"/privacy" ),
            class_ = u"header_links",
          ),
          class_ = u"wide_center_area",
        ),
        class_ = u"header",
      ),

      Span(
        *nodes
      ),

      Div(
        Div(
          Div(
            u"Copyright &copy;2008 Luminotes", u" | ",
            A( u"download", href = u"/download" ), u" | ",
            A( u"contact", href = u"/contact_info" ), u" | ",
            A( u"team", href = u"/meet_the_team" ), u" | ",
            A( u"blog", href = u"/blog" ), u" | ",
            A( u"privacy", href = u"/privacy" ),
            class_ = u"footer_links",
          ),
          class_ = u"wide_center_area",
        ),
        class_ = u"footer",
      ),
    )
