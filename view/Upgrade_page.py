from Product_page import Product_page
from Tags import Div, H1, Img, A, P, Table, Th, Tr, Td, Li, Span, I, Br, Ul, Li, Script, H4, B, Script
from config.Version import VERSION


class Upgrade_page( Product_page ):
  FOCUSED_PLAN = 2 

  def __init__( self, user, notebooks, first_notebook, login_url, logout_url, rate_plan, groups, rate_plans, unsubscribe_button ):
    MEGABYTE = 1024 * 1024
    rate_plans = list( rate_plans )
    user_plan = rate_plans[ user.rate_plan ]

    Product_page.__init__(
      self,
      user,
      first_notebook,
      login_url,
      logout_url,
      u"pricing", # note title

      Script( type = u"text/javascript", src = u"/static/js/MochiKit.js?%s" % VERSION ),

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
            ( user.rate_plan == 0 ) and u"30-day free trial on all plans." or None,
            Span( u"Upgrade, downgrade, or cancel anytime.", class_ = u"lighter_text" ),
            class_ = u"upgrade_subtitle",
          ),
          P(
            Table(
              self.fee_row( rate_plans, user ),
              self.spacer_row( rate_plans ),
              Tr(
                [ Td(
                  ( plan[ u"included_users" ] == 1 ) and
                    Span( Span( u"Single", class_ = u"highlight" ), u"user", title = u"This plan includes one user account, so it's ideal for individuals." ) or
                    Span( u"Up to", Span( "%s" % plan[ u"included_users" ], class_ = u"highlight" ), u"users", title = "This plan includes multiple accounts, including an admin area where you can create and manage users for your organization." ),
                  class_ = u"feature_value" + ( index == self.FOCUSED_PLAN and u" focused_feature_value" or u"" ),
                ) for ( index, plan ) in enumerate( rate_plans ) ],
              ),
              Tr(
                [ Td(
                  plan[ u"storage_quota_bytes" ] and
                    Span( "%s MB" % ( plan[ u"storage_quota_bytes" ] // MEGABYTE ), class_ = u"highlight" ) or
                    Span( u"unlimited", class_ = u"highlight" ),
                  u"storage",
                  title = u"Storage space for your notes, documents, and files.",
                  class_ = u"feature_value" + ( index == self.FOCUSED_PLAN and u" focused_feature_value" or u"" ),
                ) for ( index, plan ) in enumerate( rate_plans ) ],
              ),
              plan[ u"notebook_sharing"] and Tr(
                [ Td(
                  plan[ u"notebook_collaboration" ] and
                    Span( u"Invite", Span( u"editors", class_ = u"highlight"  ), title = u"Invite people to collaborate on your wiki. Share only the notebooks you want. Keep the others private." ) or
                    Span( u"Invite", Span( u"viewers", class_ = u"highlight" ), title = u"Invite people to view your wiki. Share only the notebooks you want. Keep the others private." ),
                  class_ = u"feature_value" + ( index == self.FOCUSED_PLAN and u" focused_feature_value" or u"" ),
                ) for ( index, plan ) in enumerate( rate_plans ) ],
              ) or None,
              self.button_row( rate_plans, user ),
              self.spacer_row( rate_plans, bottom = True ),
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
              of your wiki as a stand-alone web page or a CSV spreadsheet &mdash; anytime you like.
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
            H4( u"How does the 30-day free trial work?", class_ = u"upgrade_question" ),
            P(
              """
              When you subscribe to Luminotes, your first 30 days are completely free. And if you
              cancel during that period, you aren't charged a thing. During those 30 days, you have
              full access to all features of your selected subscription plan. That way, you can see
              whether Luminotes works for you without any sort of commitment.
              """,
              class_ = u"upgrade_text",
            ),
            H4( u"Once I subscribe, can I cancel anytime?", class_ = u"upgrade_question" ),
            P(
              """
              Of course. There are no contracts or cancellation fees. There are no hidden fees. You
              can upgrade, downgrade, or cancel your account anytime. Simply login to your account
              and return to this pricing page. Or, if you prefer, you can cancel your subscription
              directly from PayPal.
              """,
              class_ = u"upgrade_text",
            ),
            P(
              """
              If you cancel during your trial period, then you are not charged anything at all.
              And if you cancel anytime after the trial period ends, then your subscription is
              stopped immediately, and you are never charged again. Subscription fees that you have
              already paid still apply. You are welcome to
              """,
              A( u"contact support", href = "/contact_info" ),
              """
              with any billing questions.
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
            Div(
              u"Get two months free with a yearly subscription!",
              class_ = u"upgrade_subtitle",
            ),
            Table(
              self.fee_row( rate_plans, user, yearly = True ),
              self.spacer_row( rate_plans ),
              Tr(
                [ Td(
                  ( plan[ u"included_users" ] == 1 ) and
                    Span( Span( u"Single", class_ = u"highlight" ), u"user", title = u"This plan includes one user account, so it's ideal for individuals." ) or
                    Span( u"Up to", Span( "%s" % plan[ u"included_users" ], class_ = u"highlight" ), u"users", title = "This plan includes multiple accounts, including an admin area where you can create and manage users for your organization." ),
                  class_ = u"feature_value" + ( index == self.FOCUSED_PLAN and u" focused_feature_value" or u"" ),
                ) for ( index, plan ) in enumerate( rate_plans ) ],
              ),
              Tr(
                [ Td(
                  plan[ u"storage_quota_bytes" ] and
                    Span( "%s MB" % ( plan[ u"storage_quota_bytes" ] // MEGABYTE ), class_ = u"highlight" ) or
                    Span( u"unlimited", class_ = u"highlight" ),
                  u"storage",
                  title = u"Storage space for your notes, documents, and files.",
                  class_ = u"feature_value" + ( index == self.FOCUSED_PLAN and u" focused_feature_value" or u"" ),
                ) for ( index, plan ) in enumerate( rate_plans ) ],
              ),
              plan[ u"notebook_sharing"] and Tr(
                [ Td(
                  plan[ u"notebook_collaboration" ] and
                    Span( u"Invite", Span( u"editors", class_ = u"highlight"  ), title = u"Invite people to collaborate on your wiki. Share only the notebooks you want. Keep the others private." ) or
                    Span( u"Invite", Span( u"viewers", class_ = u"highlight" ), title = u"Invite people to view your wiki. Share only the notebooks you want. Keep the others private." ),
                  class_ = u"feature_value" + ( index == self.FOCUSED_PLAN and u" focused_feature_value" or u"" ),
                ) for ( index, plan ) in enumerate( rate_plans ) ],
              ) or None,
              self.button_row( rate_plans, user, yearly = True ),
              self.spacer_row( rate_plans, bottom = True ),
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

  def fee_row( self, rate_plans, user, yearly = False ):
    def make_fee_area( plan, index ):
      fee_area = (
        Span( plan[ u"name" ].capitalize(), class_ = u"plan_name" ),
        plan[ u"fee" ] and Div(
          yearly and Span(
            u"$%s" % plan[ u"yearly_fee" ],
            Span( u"/year", class_ = u"month_text" ),
            class_ = u"price_text",
            separator = u"",
          ) or Div(
            u"$%s" % plan[ u"fee" ],
            Span( u"/month", class_ = u"month_text" ),
            class_ = u"price_text",
            separator = u"",
          ),
        ) or Div( Div( u"No fee", class_ = u"price_text" ) ),
        Div(
          plan[ u"designed_for"] and u"For" or "&nbsp;", plan[ u"designed_for" ],
          class_ = u"small_text",
        ),
        ( index == self.FOCUSED_PLAN ) and Div( u"Best value", class_ = u"focused_text highlight" ) or None,
      )

      # if this is a demo/guest user, then make the fee area a big link to the sign up page
      if not user or user.username in ( u"anonymous", None ):
        fee_area = A( href = u"/sign_up?plan=%s&yearly=%s" % ( index, yearly ), *fee_area )
      else:
        fee_area = Span( *fee_area )

      return fee_area

    return Tr(
      [ Th(
        make_fee_area( plan, index ),
        class_ = u"plan_name_area plan_width" + ( index == self.FOCUSED_PLAN and u" focused_plan_name_area" or u"" ),
      ) for ( index, plan ) in enumerate( rate_plans ) ],
    )

  def button_row( self, rate_plans, user, yearly = False ):
    return Tr(
      [ Td(
        Div(
          # 1 = modifying an existing subscription, 0 = new subscription
          user and user.username not in ( u"anonymous", None ) and user.rate_plan != index \
               and ( yearly and ( plan.get( u"yearly_button" ) and plan.get( u"yearly_button" ).strip() and
                                  plan.get( u"yearly_button" ) % ( user.object_id, user.rate_plan and 1 or 0 ) or None ) or \
                                ( plan.get( u"button" ) and plan.get( u"button" ).strip() and
                                  plan.get( u"button" ) % ( user.object_id, user.rate_plan and 1 or 0 ) or None ) ) or None,
          ( not user or user.username in ( u"anonymous", None ) ) and A(
              Img( src = u"/static/images/sign_up_button.png", width = "76", height = "23" ),
              href = u"/sign_up?plan=%s&yearly=%s" % ( index, yearly ),
          ) or None,
          class_ = u"subscribe_button_area",
        ),
        ( user.rate_plan == 0 ) and Div( ( index > 0 ) and "30-day free trial" or "&nbsp;", class_ = u"small_text" ) or None,
        class_ = ( index == self.FOCUSED_PLAN and u"focused_feature_value" or u"" ),
       ) for ( index, plan ) in enumerate( rate_plans ) ],
    )

  def spacer_row( self, rate_plans, bottom = False ):
    border_bottom = bottom and " focused_border_bottom" or ""

    return Tr( [ Td( class_ = ( i == self.FOCUSED_PLAN and u"focused_feature_value" + border_bottom or u"spacer_row" ) ) for i in range( len( rate_plans ) ) ], class_ = u"spacer_row" )
