from Product_page import Product_page
from Tags import Div, Img, A, P, Table, Tr, Td, Li, Span, I


class Front_page( Product_page ):
  def __init__( self, user, notebooks, first_notebook, login_url, logout_url, rate_plan ):
    Product_page.__init__(
      self,
      user,
      first_notebook,
      login_url,
      logout_url,
      u"home", # note title

      Div(
        Div(
          Div(
            A(
              Img( src = u"/static/images/screenshot_small.png", width = u"400", height = u"291" ),
              href = u"/static/images/screenshot.png",
              target = u"_new",
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
          Div(
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
                u"Marvelous! Simply marvelous!",
                class_ = u"quote_title",
              ),
              u"""
              Very simple to use, and I can access it from any computer. Great idea!"
              """,
              class_ = u"quote_text",
              separator = u"",
            ),
            Div(
              u"-Lydia Newkirk",
              class_ = u"quote_signature",
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
            Table(
              Tr(
                Td(
                  A(
                    Img( src = u"/static/images/wysiwyg_thumb.png", width = u"175", height = "100", class_ = u"thumbnail" ),
                    href = u"/static/images/wysiwyg.png",
                    target = u"_new",
                  ),
                  Div( u"Create a wiki visually", class_ = u"thumbnail_caption" ),
                  Div( u"Make a wiki as easily as writing a document.", class_ = u"thumbnail_caption_detail" ),
                  class_ = u"thumbnail_cell",
                ),
                Td(
                  A(
                    Img( src = u"/static/images/big_picture_thumb.png", width = u"175", height = "100", class_ = u"thumbnail" ),
                    href = u"/static/images/big_picture.png",
                    target = u"_new",
                  ),
                  Div( u"Link your notes together", class_ = u"thumbnail_caption" ),
                  Div( u"Connect your thoughts with links between notes.", class_ = u"thumbnail_caption_detail" ),
                  class_ = u"thumbnail_cell",
                ),
              ),
              Tr(
                Td(
                  A(
                    Img( src = u"/static/images/download_thumb.png", width = u"175", height = "100", class_ = u"thumbnail" ),
                    href = u"/static/images/screenshot.png",
                    target = u"_new",
                  ),
                  Div( u"Take your wiki to go", class_ = u"thumbnail_caption" ),
                  Div( u"Download your entire wiki with a single click.", class_ = u"thumbnail_caption_detail" ),
                  class_ = u"thumbnail_cell",
                ),
                Td(
                  A(
                    Img( src = u"/static/images/share_thumb.png", width = u"175", height = "100", class_ = u"thumbnail" ),
                    href = u"/static/images/share.png",
                    target = u"_new",
                  ),
                  Div( u"Share your thoughts", class_ = u"thumbnail_caption" ),
                  Div( u"Invite friends and colleagues to collaborate.", class_ = u"thumbnail_caption_detail" ),
                  class_ = u"thumbnail_cell",
                ),
              ),
              class_ = u"thumbnail_area",
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
      P(
        Span( id = u"new_note_button_preload" ),
        Span( id = u"link_button_preload" ),
        Span( id = u"bold_button_preload" ),
        Span( id = u"italic_button_preload" ),
        Span( id = u"underline_button_preload" ),
        Span( id = u"title_button_preload" ),
        Span( id = u"bullet_list_button_preload" ),
        Span( id = u"numbered_list_button_preload" ),
      ),
    )
