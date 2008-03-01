from Page import Page
from Tags import Link, Div, Img, A, P, Table, Td, Li, Span, I


class Product_page( Page ):
  def __init__( self, user, notebooks, first_notebook, login_url, logout_url, rate_plan ):
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

      Div(
        Div(
          Div(
            A(
              Img( src = u"/static/images/screenshot_small.png", width = u"400", height = u"291" ),
              href = u"/take_a_tour",
            ),
            class_ = u"screenshot",
          ),
          Div(
            Div(
              Img(
                src = u"/static/images/hook.png",
                width = u"400", height = u"51",
                alt = u"Collect your thoughts.",
              ),
            ),
            P(
              Img(
                src = u"/static/images/sub_hook.png",
                width = u"307", height = u"54",
                alt = u"Get organized with your own Luminotes personal wiki notebook.",
              ),
            ),
            Table(
              Td(
                Li( u"Gather all of your ideas into one place." ),
                Li( u"Easily link together related concepts." ),
                Li( u"Share your wiki with anyone." ),
                align = u"left",
              ),
              align = u"center",
            ),
            P(
              A( u"Take a tour", href = u"/take_a_tour", class_ = u"hook_action" ), u", ",
              A( u"Try the demo", href = u"/users/demo", class_ = u"hook_action" ), u", ",
              Span( u" or ", class_ = u"hook_action_or" ),
              A( u"Sign up", href = u"/sign_up", class_ = u"hook_action"  ),
              class_ = u"hook_action_area",
              separator = u"",
            ),
            class_ = u"explanation",
          ),
          class_ = u"wide_center_area",
        ),
        class_ = u"hook_area",
      ),

      Div(
        Div(
          Img(
            src = u"/static/images/what_is_luminotes.png",
            class_ = u"heading", width = u"214", height = u"29",
            alt = u"What is Luminotes?",
          ),
          Div(
            P(
              u"""
              Luminotes is a personal wiki notebook for organizing your notes and ideas.
              You don't have to use any special markup codes or install any software. You
              simply start typing.
              """,
            ),
            P(
              u"""
              With Luminotes, you deal with several notes all at once on the same web page,
              so you get a big-picture view of what you're working on and can easily make
              links from one concept to another.
              """,
              A( u"Read more.", href = u"/take_a_tour" ),
            ),
            P(
              u"""
              Luminotes is open source / free software and licensed under the terms of the
              GNU GPL.
              """,
            ),
            class_ = u"what_is_luminotes_text",
          ),
          class_ = u"what_is_luminotes_area",
        ),

        Div(
          P(
            Img(
              src = u"/static/images/quotes.png",
              class_ = u"heading", width = u"253", height = u"31",
              alt = u"What people are saying",
            ),
          ),

          Div(
            Div(
              u'"',
              Span(
                u"What I love most about Luminotes is the ", I( u"simplicity" ), u" of it.",
                class_ = u"quote_title",
                separator = u"",
              ),
              u"""
              Maybe I have a touch of ADD, but I get so distracted with other products and
              all the gadgets, bells, and whistles they offer. I spend more time fiddling
              with the features than actually working. Luminotes, for me, recreates the old
              index card method we all used for term papers in high school."
              """,
              class_ = u"quote_text",
              separator = u"",
            ),
            Div(
              u"-Michael Miller, President &amp; CEO, Mighty Hero Entertainment, Inc.",
              class_ = u"quote_signature"
            ),
            class_ = u"quote",
          ),

          Div(
            Div(
              u'"',
              Span(
                u"I just wanted to thank you for the great work with Luminotes!",
                class_ = u"quote_title",
              ),
              u"""
              I use it both at home and at work, and it's a big help!"
              """,
              class_ = u"quote_text",
              separator = u"",
            ),
            Div(
              u"-Brian M.B. Keaney",
              class_ = u"quote_signature",
            ),
            class_ = u"quote",
          ),

          class_ = u"quotes_area",
        ),
        class_ = u"wide_center_area",
      ),

      Div(
        P(
          A( u"Take a tour", href = u"/take_a_tour", class_ = u"hook_action" ), u", ",
          A( u"Try the demo", href = u"/users/demo", class_ = u"hook_action" ), u", ",
          Span( u" or ", class_ = u"hook_action_or" ),
          A( u"Sign up", href = u"/sign_up", class_ = u"hook_action"  ),
          class_ = u"hook_action_area",
          separator = u"",
        ),
        class_ = u"center_area",
      ),
      P(),

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
