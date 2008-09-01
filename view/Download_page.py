from Product_page import Product_page
from Tags import Div, H1, Img, A, P, Table, Th, Tr, Td, Li, Span, I, Br, Ul, Li, Script, H4, B
from config.Version import VERSION


class Download_page( Product_page ):
  def __init__( self, user, notebooks, first_notebook, login_url, logout_url, rate_plan, groups, download_button ):
    MEGABYTE = 1024 * 1024

    Product_page.__init__(
      self,
      user,
      first_notebook,
      login_url,
      logout_url,
      u"download", # note title

      Script( type = u"text/javascript", src = u"/static/js/MochiKit.js" ),

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
            """
            Install Luminotes on your computer. 60-day money-back guarantee.
            """,
            class_ = u"upgrade_subtitle",
          ),
          Div(
            Div(
              Img( src = u"/static/images/installer_screenshot.png", width = u"350", height = u"273" ),
              class_ = u"desktop_screenshot",
            ),
            P(
              Table(
                Tr(
                  Th( u"&nbsp;" ),
                  Th(
                    u"Luminotes Desktop",
                    Div(
                      "version", VERSION,
                      class_ = u"version_text",
                    ),
                    Div(
                      download_button,
                      class_ = u"download_button_area",
                    ),
                    class_ = u"plan_name",
                  )
                ),
                Tr(
                  Td(
                    A( u"Unlimited storage space", href = u"#", onclick = u"toggleElementClass( 'undisplayed', 'storage_description' ); return false;" ),
                    class_ = u"feature_name",
                  ),
                  Td(
                    Img( src = u"/static/images/check.png", width = u"22", height = u"22" ),
                  ),
                ),
                Tr(
                  Td(
                    Ul(
                      Li( u"More space for your wiki notes." ),
                      Li( u"More space for your documents and files." ),
                    ),
                    colspan = u"2",
                    id = u"storage_description",
                    class_ = u"feature_description undisplayed",
                  ),
                ),
                Tr(
                  Td(
                    A( u"Unlimited wiki notebooks", href = u"#", onclick = u"toggleElementClass( 'undisplayed', 'notebooks_description' ); return false;" ),
                    class_ = u"feature_name",
                  ),
                  Td(
                    Img( src = u"/static/images/check.png", width = u"22", height = u"22" ),
                  ),
                ),
                Tr(
                  Td(
                    Ul(
                      Li( u"Create a unique notebook for each subject." ),
                      Li( u"Keep work and personal notebooks separate." ),
                    ),
                    colspan = u"2",
                    id = u"notebooks_description",
                    class_ = u"feature_description undisplayed",
                  ),
                ),
                Tr(
                  Td(
                    A( u"Friendly email support", href = u"#", onclick = u"toggleElementClass( 'undisplayed', 'support_description' ); return false;" ),
                    class_ = u"feature_name",
                  ),
                  Td(
                    Img( src = u"/static/images/check.png", width = u"22", height = u"22" ),
                  ),
                ),
                Tr(
                  Td(
                    Ul(
                      Li( u"Fast email responses to your support questions. From a real live human." ),
                      Li( u"No waiting on hold with a call center." ),
                    ),
                    colspan = u"2",
                    id = u"support_description",
                    class_ = u"feature_description undisplayed",
                  ),
                ),
                Tr(
                  Td(
                    A( u"Notes stored on your own computer", href = u"#", onclick = u"toggleElementClass( 'undisplayed', 'local_storage' ); return false;" ),
                    class_ = u"feature_name",
                  ),
                  Td(
                    Img( src = u"/static/images/check.png", width = u"22", height = u"22" ),
                  ),
                ),
                Tr(
                  Td(
                    Ul(
                      Li( u"All of your notes are stored privately on your own computer." ),
                      Li( u"A future release will support optional online syncing." ),
                    ),
                    colspan = u"2",
                    id = u"local_storage",
                    class_ = u"feature_description undisplayed",
                  ),
                ),
                Tr(
                  Td(
                    A( u"Works without an internet connection", href = u"#", onclick = u"toggleElementClass( 'undisplayed', 'works_offline' ); return false;" ),
                    class_ = u"feature_name",
                  ),
                  Td(
                    Img( src = u"/static/images/check.png", width = u"22", height = u"22" ),
                  ),
                ),
                Tr(
                  Td(
                    Ul(
                      Li( u"Take notes in meetings, in class, or while on the go." ),
                      Li( u"Runs in a web browser, but no internet connection is needed." ),
                    ),
                    colspan = u"2",
                    id = u"works_offline",
                    class_ = u"feature_description undisplayed",
                  ),
                ),
                border = u"1",
                id = u"upgrade_table",
              ),
              class_ = u"upgrade_table_area",
            ),
            class_ = u"wide_center_area",
          ),

          class_ = u"upgrade_area",
        ),

        Div(
          Div(
            H4( u"What operating systems are supported?", class_ = u"upgrade_question" ),
            P(
              u"""
              Luminotes Desktop currently supports Windows XP and Windows Vista.
              Linux users should get the
              """,
              A( u"source code", href = "/source_code" ),
              "directly. And future releases will support Mac OS X as well.",
              class_ = u"upgrade_text",
            ),
            P(
              u"""
              If Luminotes Desktop does not support your operating system currently, or you just
              don't want to install anything on your computer, you can still use Luminotes
              online! Simply
              """,
              A( u"sign up", href = "/pricing" ),
              """
              for an online Luminotes account. With the online version of Luminotes, there's
              nothing to download or install.
              """,
              class_ = u"upgrade_text",
            ),
            H4( u"How many users are supported?", class_ = u"upgrade_question" ),
            P(
              u"""
              Luminotes Desktop is designed for individual note taking. If you're interested
              in sharing and collaboration, take a look at
              """,
              A( u"the online version of Luminotes", href = "/pricing" ),
              """
              for those features.
              """,
              class_ = u"upgrade_text",
            ),
            H4( u"Is my wiki private?", class_ = u"upgrade_question" ),
            P(
              u"""
              Absolutely. With Luminotes Desktop, your notes are stored locally on your own
              computer, not on the web. But if you do want to access your wiki both locally
              and online, a future release will include optional online synchronization.
              There is also a complete
              """,
              A( u"Luminotes privacy policy", href = "/privacy" ),
              u"""
              so please check that out if you're interested in how Luminotes
              protects your privacy.
              """,
              class_ = u"upgrade_text",
            ),
            H4( u"Are upgrades included?", class_ = u"upgrade_question" ),
            P(
              """
              When you purchase Luminotes Desktop, you automatically get full access to all future
              upgrades.
              """,
              class_ = u"upgrade_text",
            ),
            H4( u"Can I try before I buy?", class_ = u"upgrade_question" ),
            P(
              """
              Absolutely! Just check out the full-featured
              """,
              A( u"online demo", href = "/users/demo" ),
              """
              to see Luminotes for yourself. The only difference is that Luminotes Desktop runs in
              a browser on your own computer instead of on the web.
              """,
              class_ = u"upgrade_text",
            ),
            H4( u"What forms of payment do you accept?", class_ = u"upgrade_question" ),
            P(
              """
              When you click the "Buy Now" button above, you'll be presented with a simple checkout
              page. You can purchase Luminotes Desktop with either a credit card or PayPal. It's
              fast and secure. You do not need a PayPal account to make the purchase.
              """,
              class_ = u"upgrade_text",
            ),
            P(
              """
              After you fill out the payment information, you will be able to download Luminotes
              Desktop and start taking notes right away.
              """,
              class_ = u"upgrade_text",
            ),
            H4( u"What is your refund policy?", class_ = u"upgrade_question" ),
            P(
              """
              It's this simple: Luminotes Desktop comes with a 60-day money-back guarantee. No questions asked.
              """,
              class_ = u"upgrade_text",
            ),
            H4( u"What happens to my wiki if I stop using Luminotes?", class_ = u"upgrade_question" ),
            P(
              """
              There is no lock-in with Luminotes. You can export your entire wiki whenever you like.
              """,
              class_ = u"upgrade_text",
            ),
            class_= u"wide_center_area",
          ),

          P(
            Table(
              Tr(
                Th(
                  u"Luminotes Desktop",
                  Div(
                    download_button,
                    class_ = u"download_button_area",
                  ),
                  class_ = u"plan_name",
                )
              ),
              id = u"upgrade_table_small",
            ),
            class_= u"upgrade_table_area",
          ),

          Div(
            P(
              Span( u"Have a question before you buy?", class_ = u"hook_action_question" ), Br(),
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
