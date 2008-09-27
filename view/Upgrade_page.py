from Product_page import Product_page
from Tags import Div, H1, Img, A, P, Table, Th, Tr, Td, Li, Span, I, Br, Ul, Li, Script, H4, B


class Upgrade_page( Product_page ):
  def __init__( self, user, notebooks, first_notebook, login_url, logout_url, rate_plan, groups, rate_plans, unsubscribe_button ):
    MEGABYTE = 1024 * 1024
    rate_plans = list( rate_plans )
    user_plan = rate_plans[ user.rate_plan ]
    rate_plans.reverse() # show rate plans highest to lowest

    Product_page.__init__(
      self,
      user,
      first_notebook,
      login_url,
      logout_url,
      u"pricing", # note title

      Script( type = u"text/javascript", src = u"/static/js/MochiKit.js" ),

      Div(
        Div(
          user and user.username not in ( None, u"anonymous" ) and H1(
            Img(
              src = u"/static/images/upgrade.png",
              width = u"152", height = u"51",
              alt = u"upgrade",
            ),
          ) or H1(
            Img(
              src = u"/static/images/sign_up.png",
              width = u"138", height = u"51",
              alt = u"sign up",
            ),
          ),
          P(
            """
            Upgrade, downgrade, or cancel anytime. 60-day money-back guarantee.
            """,
            class_ = u"upgrade_subtitle",
          ),
          P(
            Table(
              self.fee_row( rate_plans, user ),
              Tr(
                Td(
                  u"Designed for",
                  class_ = u"feature_name",
                ),
                [ Td(
                  plan[ u"designed_for" ],
                  class_ = u"feature_value",
                ) for plan in rate_plans ],
              ),
              Tr(
                Td(
                  A( u"Included accounts", href = u"#", onclick = u"toggleElementClass( 'undisplayed', 'users_description' ); return false;" ),
                  class_ = u"feature_name",
                ),
                [ Td(
                  ( plan[ u"included_users" ] == 1 ) and u"1 user" or "up to<br>%s users" % plan[ u"included_users" ],
                  class_ = u"feature_value",
                ) for plan in rate_plans ],
              ),
              Tr(
                Td(
                  Ul(
                    Li( u"Collaborate on a wiki with multiple people in your organization." ),
                    Li( u"Even collaborate with other Luminotes users beyond your included accounts." ),
                    Li( u"Only one subscription is necessary." ),
                  ),
                  colspan = len( rate_plans ) + 1,
                  id = u"users_description",
                  class_ = u"feature_description undisplayed",
                ),
              ),
              Tr(
                Td(
                  A( u"Included storage space", href = u"#", onclick = u"toggleElementClass( 'undisplayed', 'storage_description' ); return false;" ),
                  class_ = u"feature_name",
                ),
                [ Td(
                  plan[ u"storage_quota_bytes" ] and "%s MB" % ( plan[ u"storage_quota_bytes" ] // MEGABYTE ) or u"unlimited",
                ) for plan in rate_plans ],
              ),
              Tr(
                Td(
                  Ul(
                    Li( u"More space for your wiki notes." ),
                    Li( u"More space for your documents and files." ),
                    Li( u"All of your users share a common pool of storage space." ),
                  ),
                  colspan = len( rate_plans ) + 1,
                  id = u"storage_description",
                  class_ = u"feature_description undisplayed",
                ),
              ),
              Tr(
                Td(
                  A( u"Unlimited wiki notebooks", href = u"#", onclick = u"toggleElementClass( 'undisplayed', 'notebooks_description' ); return false;" ),
                  class_ = u"feature_name",
                ),
                [ Td(
                  Img( src = u"/static/images/check.png", width = u"22", height = u"22" ),
                ) for plan in rate_plans ],
              ),
              Tr(
                Td(
                  Ul(
                    Li( u"Create a unique notebook for each subject." ),
                    Li( u"Keep work and personal notebooks separate." ),
                  ),
                  colspan = len( rate_plans ) + 1,
                  id = u"notebooks_description",
                  class_ = u"feature_description undisplayed",
                ),
              ),
              Tr(
                Td(
                  A( u"Friendly email support", href = u"#", onclick = u"toggleElementClass( 'undisplayed', 'support_description' ); return false;" ),
                  class_ = u"feature_name",
                ),
                [ Td(
                  Img( src = u"/static/images/check.png", width = u"22", height = u"22" ),
                ) for plan in rate_plans ],
              ),
              Tr(
                Td(
                  Ul(
                    Li( u"Fast email responses to your support questions. From a real live human." ),
                    Li( u"No waiting on hold with a call center." ),
                  ),
                  colspan = len( rate_plans ) + 1,
                  id = u"support_description",
                  class_ = u"feature_description undisplayed",
                ),
              ),
              Tr(
                Td(
                  A( u"Invite people to view your wiki", href = u"#", onclick = u"toggleElementClass( 'undisplayed', 'view_description' ); return false;" ),
                  class_ = u"feature_name",
                ),
                [ Td(
                  plan[ u"notebook_sharing" ] and
                  Img( src = u"/static/images/check.png", width = u"22", height = u"22" ) or u"&nbsp",
                ) for plan in rate_plans ],
              ),
              Tr(
                Td(
                  Ul(
                    Li( u"Invite specific people to read your wiki." ),
                    Li( u"Invite as many people as you want." ),
                    Li( u"Share only the notebooks you want to share. Keep the others private." ),
                  ),
                  colspan = len( rate_plans ) + 1,
                  id = u"view_description",
                  class_ = u"feature_description undisplayed",
                ),
              ),
              Tr(
                Td(
                  A( u"Invite people to edit your wiki", href = u"#", onclick = u"toggleElementClass( 'undisplayed', 'edit_description' ); return false;" ),
                  class_ = u"feature_name",
                ),
                [ Td(
                  plan[ u"notebook_collaboration" ] and
                  Img( src = u"/static/images/check.png", width = u"22", height = u"22" ) or u"&nbsp",
                ) for plan in rate_plans ],
              ),
              Tr(
                Td(
                  Ul(
                    Li( u"Invite specific people to collaborate on your wiki." ),
                    Li( u"Decide who can edit and who can only view." ),
                    Li( u"Invite as many people as you want. They only need free Luminotes accounts." ),
                    Li( u"Revoke collaboration access with a single click." ),
                    Li( u"Share only the notebooks you want to share. Keep the others private." ),
                  ),
                  colspan = len( rate_plans ) + 1,
                  id = u"edit_description",
                  class_ = u"feature_description undisplayed",
                ),
              ),
              Tr(
                Td(
                  A( u"User administration", href = u"#", onclick = u"toggleElementClass( 'undisplayed', 'admin_description' ); return false;" ),
                  class_ = u"feature_name",
                ),
                [ Td(
                  plan[ u"user_admin" ] and
                  Img( src = u"/static/images/check.png", width = u"22", height = u"22" ) or u"&nbsp",
                ) for plan in rate_plans ],
              ),
              Tr(
                Td(
                  Ul(
                    Li( u"Manage all Luminotes accounts for your organization from one web page." ),
                    Li( u"Create and delete users as needed." ),
                  ),
                  colspan = len( rate_plans ) + 1,
                  id = u"admin_description",
                  class_ = u"feature_description undisplayed",
                ),
              ),
              border = u"1",
              id = u"upgrade_table",
            ),
            class_ = u"upgrade_table_area",
          ),

          user and user.username not in ( u"anonymous", None ) and P(
            u"You're currently subscribed to Luminotes %s." % 
            user_plan[ u"name" ].capitalize(),
            ( user.rate_plan > 0 ) and unsubscribe_button or None,
          ) or None,

          P(
            u"Get two months free with a ", A( u"yearly subscription", href = "#yearly" ), u"!",
            separator = "",
            class_ = u"yearly_link",
          ),

          Div(
            u"Don't want to take notes online? ",
            A( u"Download Luminotes Desktop", href = u"/download" ),
            u".",
            class_ = u"small_text",
            separator = u"",
          ),

          class_ = u"upgrade_area",
        ),

        Div(
          Div(
            H4( u"Which plan is right for me?", class_ = u"upgrade_question" ),
            P(
              u"The", B( u"Standard" ), u"and", B( u"Basic" ),
              u"""
              plans are designed for individuals, allowing you to invite as
              many people as you like to view or edit your wiki. They only need free Luminotes
              accounts.
              """,
              class_ = u"upgrade_text",
            ),
            P(
              u"The", B( u"Premium" ), u"and", B( u"Plus" ),
              u"""
              plans are designed for teams and organizations, allowing you to create and manage your
              own user accounts. In addition, you can invite as many people as you like to view or
              edit your wiki, whether they're a user you created or they just have a free
              Luminotes account.
              """,
              class_ = u"upgrade_text",
            ),
            H4( u"Do you have a desktop version I can download?", class_ = u"upgrade_question" ),
            P(
              u"""
              Yes! If you want to download Luminotes and take notes locally instead of on the web,
              check out
              """,
              A( u"Luminotes Desktop", href = "/download" ), ".",
              separator = u"",
              class_ = u"upgrade_text",
            ),
            H4( u"Is my wiki private?", class_ = u"upgrade_question" ),
            P(
              u"""
              Absolutely. Your personal wiki is protected by industry-standard SSL encryption, and
              your wiki is never shared with anyone unless you explicitly invite them to view or
              edit it. There is a complete
              """,
              A( u"Luminotes privacy policy", href = "/privacy" ),
              u"""
              on the subject, so please check that out if you're interested in how Luminotes
              protects your privacy.
              """,
              class_ = u"upgrade_text",
            ),
            H4( u"Do you backup my wiki?", class_ = u"upgrade_question" ),
            P(
              """
              Your wiki is fully backed up every day, and you can even download the entire contents
              of your wiki by clicking "download as html" whenever you want.
              """,
              class_ = u"upgrade_text",
            ),
            H4( u"How does upgrading work?", class_ = u"upgrade_question" ),
            P(
              """
              When you upgrade your Luminotes account, you'll be presented with a simple PayPal
              checkout page. If you already have a PayPal account, you can upgrade your Luminotes
              account in a matter of seconds. If you don't yet have a PayPal account, no problem.
              Just enter your payment information. It's fast and secure.
              """,
              class_ = u"upgrade_text",
            ),
            P(
              """
              After you subscribe, your Luminotes account will be upgraded automatically so you can
              start enjoying your new plan's benefits right away.
              """,
              class_ = u"upgrade_text",
            ),
            H4( u"Once I subscribe, can I cancel anytime?", class_ = u"upgrade_question" ),
            P(
              """
              Of course. This isn't a cell phone plan. There are no contracts or cancellation fees.
              You can upgrade, downgrade, or cancel your account anytime. Simply login to your
              account and return to this pricing page.
              """,
              class_ = u"upgrade_text",
            ),
            H4( u"What is your refund policy?", class_ = u"upgrade_question" ),
            P(
              """
              It's this simple: Luminotes comes with a 60-day money-back guarantee. No questions asked.
              """,
              class_ = u"upgrade_text",
            ),
            H4( u"What happens to my wiki if I cancel my subscription?", class_ = u"upgrade_question" ),
            P(
              """
              There is no lock-in with Luminotes. So if you cancel your subscription, you're simply
              returned to the free account level without losing access to your wiki. And of course
              you can download your entire wiki whenever you like.
              """,
              class_ = u"upgrade_text",
            ),
            class_= u"wide_center_area",
          ),

          P(
            A( name = "yearly" ),
            Table(
              Tr( Td(
                u"Get two months free with a yearly subscription!",
                class_ = u"upgrade_subtitle",
                colspan = u"%d" % len( rate_plans ),
              ), colspan = u"%d" % len( rate_plans ) ),
              self.fee_row( rate_plans, user, include_blank = False, yearly = True ),
              Tr(
                [ Td(
                  ( plan[ u"included_users" ] == 1 ) and u"1 user" or "up to<br />%s users" % plan[ u"included_users" ],
                  class_ = u"feature_value",
                ) for plan in rate_plans ],
              ),
              Tr(
                [ Td(
                  plan[ u"storage_quota_bytes" ] and "%s MB" % ( plan[ u"storage_quota_bytes" ] // MEGABYTE ) or u"unlimited",
                ) for plan in rate_plans ],
              ),
              border = u"1",
              id = u"upgrade_table_small",
            ),
            class_= u"upgrade_table_area",
          ),

          Div(
            P(
              Span( u"Have a question before you sign up?", class_ = u"hook_action_question" ), Br(),
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

  def fee_row( self, rate_plans, user, include_blank = True, yearly = False ):
    last_index = len( rate_plans ) - 1
    plan_list = []

    for ( index, plan ) in enumerate( rate_plans ):
      plan_list.append( ( last_index - index, plan ) )

    return Tr(
      include_blank and Th( u"&nbsp;" ) or None,
      [ Th(
        plan[ u"name" ].capitalize(),
        plan[ u"fee" ] and Div(
          yearly and Span(
            u"$%s" % plan[ u"yearly_fee" ],
            Span( u"/year", class_ = u"month_text" ),
            class_ = u"price_text",
            separator = u"",
          ) or Span(
            u"$%s" % plan[ u"fee" ],
            Span( u"/month", class_ = u"month_text" ),
            class_ = u"price_text",
            separator = u"",
          ),
          user and user.username not in ( u"anonymous", None ) and user.rate_plan != index \
               and ( yearly and ( plan.get( u"yearly_button" ).strip() and plan.get( u"yearly_button" ) % user.object_id or None ) or \
                                ( plan.get( u"button" ).strip() and plan.get( u"button" ) % user.object_id or None ) ) or None,
        ) or Div( Span( u"No fee", class_ = u"price_text" ) ),
        ( not user or user.username in ( u"anonymous", None ) ) and Div(
          A(
            Img( src = u"/static/images/sign_up_button.png", width = "76", height = "23" ),
            href = u"/sign_up?plan=%s&yearly=%s" % ( index, yearly ),
          ),
          class_ = u"sign_up_button_area",
        ) or None,
        class_ = u"plan_name",
      ) for ( index, plan ) in plan_list ],
    )
