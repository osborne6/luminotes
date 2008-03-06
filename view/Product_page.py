from Page import Page
from Tags import Link, Div, Img, A, Span


class Product_page( Page ):
  def __init__( self, user, first_notebook, login_url, logout_url, note_title, *nodes ):
    title_image = Img(
      src ="/static/images/luminotes_title.png",
      class_ = u"luminotes_title", width = u"193", height = u"60",
      alt = u"Luminotes",
    )
    Page.__init__(
      self,
      None, # use the default title
      Link( rel = u"stylesheet", type = u"text/css", href = u"/static/css/product.css" ),

      Div(
        Div(
          ( note_title == u"home" ) and title_image or A( title_image, href = u"/" ),   
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
            ( note_title == u"home" ) and Span( u"home", class_ = u"bold_link" ) or A( u"home", href = u"/" ), u" | ",
            ( note_title == u"tour" ) and Span( u"tour", class_ = u"bold_link" ) or A( u"tour", href = u"/tour" ), u" | ",
            ( note_title == u"demo" ) and Span( u"demo", class_ = u"bold_link" ) or A( u"demo", href = u"/users/demo" ), u" | ",
            ( note_title == u"upgrade" ) and Span( u"upgrade", class_ = u"bold_link" ) or A( u"pricing", href = u"/upgrade" ), u" | ",
            ( note_title == u"faq" ) and Span( u"faq", class_ = u"bold_link" ) or A( u"faq", href = u"/faq" ), u" | ",
            ( note_title == u"guide" ) and Span( u"guide", class_ = u"bold_link" ) or A( u"help", href = u"/guide" ), u" | ",
            ( note_title == u"contact" ) and Span( u"contact", class_ = u"bold_link" ) or A( u"contact", href = u"/contact_info" ), u" | ",
            ( note_title == u"team" ) and Span( u"team", class_ = u"bold_link" ) or A( u"team", href = u"/meet_the_team" ), u" | ",
            ( note_title == u"blog" ) and Span( u"blog", class_ = u"bold_link" ) or A( u"blog", href = u"/blog" ), u" | ",
            ( note_title == u"privacy" ) and Span( u"privacy", class_ = u"bold_link" ) or A( u"privacy", href = u"/privacy" ),
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
