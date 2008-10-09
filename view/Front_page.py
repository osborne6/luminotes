from Product_page import Product_page
from Tags import Div, Img, A, P, Table, Tr, Td, Li, Span, I, Br, Ul, Li


class Front_page( Product_page ):
  def __init__( self, user, notebooks, first_notebook, login_url, logout_url, rate_plan, groups ):
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
              Img( src = u"/static/images/screenshot_small.png", width = u"400", height = u"308" ),
              href = u"/tour",
            ),
            class_ = u"front_screenshot",
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
                Li( u"As simple to use as index cards." ),
                align = u"left",
              ),
              align = u"center",
            ),
            P(
              A( u"Take a tour", href = u"/tour", class_ = u"hook_action" ), u", ",
              A( u"Try the demo", href = u"/users/demo", class_ = u"hook_action" ), u", ", Br(),
              A( u"Download", href = u"/download", class_ = u"hook_action" ), u", ",
              Span( u" or ", class_ = u"hook_action_or" ),
              A( u"Sign up", href = u"/pricing", class_ = u"hook_action"  ),
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
                u"Luminotes is a wiki without the markup learning curve.",
                class_ = u"quote_title",
                separator = u"",
              ),
              u"""
              ... Luminotes has you simply start typing, using familiar rich text buttons to add bullets and other styling, and a simple linking and tagging system for your notes."
              """,
              class_ = u"quote_text",
              separator = u"",
            ),
            Div(
              u"-Kevin Purdy, ", A( u"Review on Lifehacker", href = u"http://lifehacker.com/386813/luminotes-is-a-wiki-without-the-markup-learning-curve" ),
              class_ = u"quote_signature"
            ),
            class_ = u"quote",
          ),

          Div(
            Div(
              u'"',
              Span(
                u"Imagine an application that combines the features of a wiki and a web-based notebook.",
                class_ = u"quote_title",
                separator = u"",
              ),
              u"""
              ... as a multi-user notebook that allows you to quickly take notes and collaborate on them with other users, Luminotes is unbeatable."
              """,
              class_ = u"quote_text",
              separator = u"",
            ),
            Div(
              u"-Dmitri Popov, ", A( u"Review on Linux.com", href = u"http://www.linux.com/feature/132297" ),
              class_ = u"quote_signature"
            ),
            class_ = u"quote",
          ),

          Div(
            Div(
              u'"',
              Span(
                u"As soon as I saw Luminotes I knew it was what I and my students needed.",
                class_ = u"quote_title",
                separator = u"",
              ),
              u"""
              Clear, easy to use and beautifully simple."
              """,
              class_ = u"quote_text",
              separator = u"",
            ),
            Div(
              u"-Jonathan Lecun, Director, ", A( u"UK Teachers Online", href = u"http://www.ukteachersonline.co.uk/" ),
              class_ = u"quote_signature"
            ),
            class_ = u"quote",
          ),

          Div(
            Div(
              u'"',
              Span(
                u"Luminotes has saved me an immense amount of time with my current novel.",
                class_ = u"quote_title",
              ),
              u"""
              No more digging through mounds of text or trying to make sense of notes scrawled on random pages of my notebook months ago."
              """,
              class_ = u"quote_text",
              separator = u"",
            ),
            Div(
              u"Michail Velichansky, ", A( u"Writer", href = u"http://aggrocomic.com/" ),
              class_ = u"quote_signature",
            ),
            class_ = u"quote",
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
                u"I'm a wiki addict, so I've tried most of them, desktop and web-based.",
                class_ = u"quote_title",
                separator = u"",
              ),
              u"""
              What I like about your excellent product is the modeless editing (no edit
              and save buttons). This makes Luminotes the fastest web-based wiki I have
              used."
              """,
              class_ = u"quote_text",
              separator = u"",
            ),
            Div(
              u"-Scott Tiner, Technical Writer",
              class_ = u"quote_signature"
            ),
            class_ = u"quote",
          ),

          Div(
            Div(
              u'"',
              Span(
                u"I came across your software using the WikiMatrix comparison and fell in love instantly.",
                class_ = u"quote_title",
                separator = u"",
              ),
              u"""
              This is probably the best personal wiki software I have seen to date. Playing with
              the demo sold me completely. The design, interface, usage, and above all how bloody
              easy it is is perfect."
              """,
              class_ = u"quote_text",
              separator = u"",
            ),
            Div(
              u"-Kyle Gruel",
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
              Luminotes is a WYSIWYG personal wiki notebook for organizing your notes and ideas.
              It's designed for note taking and note keeping without the hassle
              of learning special markup codes. You simply start typing.
              """,
            ),
            Table(
              Tr(
                Td(
                  A(
                    Img( src = u"/static/images/wysiwyg_thumb.png", width = u"175", height = "100", class_ = u"thumbnail" ),
                    href = u"/tour",
                  ),
                  Div( u"Create a wiki visually", class_ = u"thumbnail_caption" ),
                  Div( u"Make a wiki as easily as writing a document.", class_ = u"thumbnail_caption_detail" ),
                  class_ = u"thumbnail_cell",
                ),
                Td(
                  A(
                    Img( src = u"/static/images/connect_thumb.png", width = u"175", height = "100", class_ = u"thumbnail" ),
                    href = u"/tour",
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
                    href = u"/tour",
                  ),
                  Div( u"Take your wiki to go", class_ = u"thumbnail_caption" ),
                  Div( u"Download your wiki as a web page or spreadsheet.", class_ = u"thumbnail_caption_detail" ),
                  class_ = u"thumbnail_cell",
                ),
                Td(
                  A(
                    Img( src = u"/static/images/share_thumb.png", width = u"175", height = "100", class_ = u"thumbnail" ),
                    href = u"/tour",
                  ),
                  Div( u"Share your thoughts", class_ = u"thumbnail_caption" ),
                  Div( u"Invite friends and colleagues to collaborate.", class_ = u"thumbnail_caption_detail" ),
                  class_ = u"thumbnail_cell",
                ),
              ),
              class_ = u"thumbnail_area",
            ),
            P(
              u"What can you do with Luminotes?",
            ),
            Ul(
              Li( u"Outline a story" ),
              Li( u"Plan a trip" ),
              Li( u"Collect recipes" ),
              Li( u"Record your ideas" ),
              Li( u"Keep track of your tasks" ),
              Li( u"Take notes" ),
              class_ = u"compact_list",
            ),
            P(
              u"""
              Luminotes is open source / free software and licensed under the terms of the
              GNU GPL.
              """,
            ),
            class_ = u"what_is_luminotes_text",
          ),
          Div(
            P(
              Span( u"Sound interesting?", class_ = u"hook_action_question" ), Br(),
              A( u"Take a tour", href = u"/tour", class_ = u"hook_action" ), u", ",
              A( u"Try the demo", href = u"/users/demo", class_ = u"hook_action" ), u", ", Br(),
              A( u"Download", href = u"/download", class_ = u"hook_action" ), u", ",
              Span( u" or ", class_ = u"hook_action_or" ),
              A( u"Sign up", href = u"/pricing", class_ = u"hook_action"  ),
              class_ = u"hook_action_area",
              separator = u"",
            ),
          ),
          class_ = u"what_is_luminotes_area",
        ),

        class_ = u"wide_center_area",
      ),

      P(
        Span( id = u"new_note_button_preload" ),
        Span( id = u"link_button_preload" ),
        Span( id = u"bold_button_preload" ),
        Span( id = u"italic_button_preload" ),
        Span( id = u"underline_button_preload" ),
        Span( id = u"strikethrough_button_preload" ),
        Span( id = u"title_button_preload" ),
        Span( id = u"bullet_list_button_preload" ),
        Span( id = u"numbered_list_button_preload" ),
        Span( id = u"note_icon_preload" ),
      ),
    )
