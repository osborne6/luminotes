from Product_page import Product_page
from Tags import Div, H1, Img, A, P, Table, Th, Tr, Td, Li, Span, I, Br, Ul, Li, Script, H4, B
from config.Version import VERSION


class Download_page( Product_page ):
  def __init__( self, user, notebooks, first_notebook, login_url, logout_url, rate_plan, groups, download_products, upgrade = False ):
    MEGABYTE = 1024 * 1024

    # for now, just assume there's a single download package
    news_url = u"http://luminotes.com/hg/luminotes/file/%s/NEWS" % VERSION

    Product_page.__init__(
      self,
      user,
      first_notebook,
      login_url,
      logout_url,
      u"download", # note title

      Script( type = u"text/javascript", src = u"/static/js/MochiKit.js?%s" % VERSION ),

      Div(
        Div(
          H1(
            Img(
              src = u"/static/images/download.png",
              width = u"181", height = u"41",
              alt = u"download",
            ),
          ),
          P(
            u"Install Luminotes on your computer.",
            class_ = u"upgrade_subtitle",
          ),
          Div(
            upgrade and Div(
              P(
                B( "Upgrading:" ),
                u"""
                If you already have Luminotes Desktop and would like to upgrade to a newer
                version, simply download and install it. All of your notes will be preserved.
                """,
                A( "Check out what's new in version %s" % VERSION, href = news_url ),
              ),
              P(
                u"Need help? Please",
                A( u"contact support", href = u"/contact_info" ),
                u"for assistance.",
              ),
              class_ = u"upgrade_text",
            ) or None,
            Div(
              Img( src = u"/static/images/installer_screenshot.png", width = u"350", height = u"273" ),
              class_ = u"desktop_screenshot",
            ),
            P(
              Table(
                Tr(
                  Th(
                    Span( u"Luminotes Desktop", class_ = u"plan_name" ),
                    Div(
                      A( "version", VERSION, href = news_url ),
                      class_ = u"version_text",
                    ),
                    class_ = u"plan_name_area download_plan_width",
                    colspan = "2",
                  ),
                ),
                Tr( Td( colspan = "2" ), class_ = u"spacer_row" ),
                Tr(
                  Td(
                    Span( u"Solo", class_ = u"highlight" ), u"note taking",
                    title = u"Luminotes Desktop is designed for individuals.",
                    class_ = u"feature_value",
                    colspan = "2",
                  ),
                ),
                Tr(
                  Td(
                    u"Runs on your", Span( u"own computer", class_ = u"highlight" ),
                    title = u"All of your notes are stored privately on your own computer or on a USB drive.",
                    class_ = u"feature_value",
                    colspan = "2",
                  ),
                ),
                Tr(
                  Td(
                    Span( u"Unlimited", class_ = u"highlight" ), u"storage",
                    title = u"Add as many notes, documents, and files as you want.",
                    class_ = u"feature_value",
                    colspan = "2",
                  ),
                ),
                Tr(
                  Td(
                    u"Works", Span( "offline", class_ = u"highlight" ),
                    title = u"Take notes in meetings, in class, or while on the go. Runs in a web browser, but doesn't need an internet connection.",
                    class_ = u"feature_value",
                    colspan = "2",
                  ),
                ),
                Tr( Td( colspan = "2" ), class_ = u"spacer_row" ),
                Tr(
                  Td(
                    u"Windows XP/Vista,", A( u"Linux source", href = u"/source_code" ),
                    class_ = u"small_text",
                    colspan = "2",
                  ),
                ),
                Tr(
                  Td(
                    u"Firefox 2+, Internet Explorer 7, Chrome 1+, Safari 3+",
                    class_ = u"small_text",
                    colspan = "2",
                  ),
                ),
                Tr( Td( colspan = "2" ), class_ = u"spacer_row" ),
                Tr(
                  Td(
                    Div(
                      A(
                        Img(
                          src = u"/static/images/trial_button.png",
                          width = u"107", height = u"26",
                          alt = u"download trial",
                        ),
                        href = "/static/luminotes.exe",
                      ),
                      class_ = u"trial_button_area",
                    ),
                    colspan = "1",
                  ) or None,
                ),
                Tr( Td( colspan = "2" ), class_ = u"spacer_row" ),
                border = u"1",
                id = u"upgrade_table",
              ),
              class_ = u"upgrade_table_area",
            ),
            class_ = u"wide_center_area",
          ),
          Div(
            u"Don't want to install anything? Need collaboration features? ",
            A( u"Use Luminotes online", href = u"/pricing" ),
            u".",
            class_ = u"small_text luminotes_online_link_area",
            separator = u"",
          ),

          class_ = u"upgrade_area",
        ),

        Div(
          Div(
            H4( u"Is my wiki private?", class_ = u"upgrade_question" ),
            P(
              u"""
              Absolutely. With Luminotes Desktop, your notes are stored locally on your own
              computer, not on the web. There is also a complete
              """,
              A( u"Luminotes privacy policy", href = "/privacy" ),
              u"""
              so please check that out if you're interested in how Luminotes
              protects your privacy.
              """,
              class_ = u"upgrade_text",
            ),
            H4( u"Can I run Luminotes Desktop from a USB flash drive?", class_ = u"upgrade_question" ),
            P(
              """
              Yes! You can keep your wiki in your pocket by running Luminotes Desktop directly from
              a USB flash drive. Full instructions are included with the download.
              """,
              class_ = u"upgrade_text",
            ),
            H4( u"What happens to my wiki if I stop using Luminotes?", class_ = u"upgrade_question" ),
            P(
              """
              There is no lock-in with Luminotes. You can export your entire wiki to a stand-alone web page or a CSV spreadsheet &mdash; anytime you like.
              """,
              class_ = u"upgrade_text",
            ),
            class_= u"wide_center_area",
          ),

          P(
            Table(
              Tr(
                Th(
                  Span( u"Luminotes Desktop", class_ = u"plan_name" ),
                  class_ = u"plan_name_area",
                  colspan = "2",
                )
              ),
              Tr(
                Td(
                  Div(
                    A(
                      Img(
                        src = u"/static/images/trial_button.png",
                        width = u"107", height = u"26",
                        alt = u"download trial",
                      ),
                      href = "/static/luminotes.exe",
                    ),
                    class_ = u"trial_button_area",
                  ),
                  colspan = "1",
                ),
              ),
              id = u"upgrade_table_small",
            ),
            class_= u"upgrade_table_area",
          ),

          Div(
            P(
              Span( u"Have a question?", class_ = u"hook_action_question" ), Br(),
              A( u"Contact support", href = u"/contact_info", class_ = u"hook_action" ),
              class_ = u"hook_action_area",
              separator = u"",
            ),
            class_ = u"center_area",
          ),

          class_ = u"wide_center_area",
        ),
      ),
    )
