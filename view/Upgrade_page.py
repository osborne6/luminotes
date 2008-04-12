from Product_page import Product_page
from Tags import Div, Img, A, P, Table, Th, Tr, Td, Li, Span, I, Br, Ul, Li


class Upgrade_page( Product_page ):
  def __init__( self, user, notebooks, first_notebook, login_url, logout_url, rate_plan, rate_plans, unsubscribe_button ):
    MEGABYTE = 1024 * 1024

    Product_page.__init__(
      self,
      user,
      first_notebook,
      login_url,
      logout_url,
      u"pricing", # note title

      Div(
        Div(
          user and user.username not in ( None, u"anonymous" ) and Div(
            Img(
              src = u"/static/images/upgrade.png",
              width = u"152", height = u"51",
              alt = u"Upgrade",
            ),
          ) or Div(
            Img(
              src = u"/static/images/sign_up.png",
              width = u"138", height = u"51",
              alt = u"Sign Up",
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
                Td( u"Included storage space", class_ = u"feature_name" ),
                [ Td(
                  plan[ u"storage_quota_bytes" ] // MEGABYTE, " MB",
                ) for plan in rate_plans ],
              ),
              Tr(
                Td( u"Unlimited wiki notebooks", class_ = u"feature_name" ),
                [ Td(
                  Img( src = u"/static/images/check.png", width = u"22", height = u"22" ),
                ) for plan in rate_plans ],
              ),
              Tr(
                Td( u"Friendly email support", class_ = u"feature_name" ),
                [ Td(
                  Img( src = u"/static/images/check.png", width = u"22", height = u"22" ),
                ) for plan in rate_plans ],
              ),
              Tr(
                Td( u"Invite people to view your wiki", class_ = u"feature_name" ),
                [ Td(
                  Img( src = u"/static/images/check.png", width = u"22", height = u"22" ),
                ) for plan in rate_plans ],
              ),
              Tr(
                Td( u"Invite people to edit your wiki", class_ = u"feature_name" ),
                [ Td(
                  plan[ u"notebook_collaboration" ] and
                  Img( src = u"/static/images/check.png", width = u"22", height = u"22" ) or u"&nbsp",
                ) for plan in rate_plans ],
              ),
              Tr(
                Td( u"Wiki access control", class_ = u"feature_name" ),
                [ Td(
                  plan[ u"notebook_collaboration" ] and
                  Img( src = u"/static/images/check.png", width = u"22", height = u"22" ) or u"&nbsp",
                ) for plan in rate_plans ],
              ),
              border = u"1",
              id = u"upgrade_table",
            ),
            class_ = u"upgrade_table_area",
          ),

          user and user.username not in ( u"anonymous", None ) and P(
            u"You're currently subscribed to Luminotes %s." % 
            rate_plans[ user.rate_plan ][ u"name" ].capitalize(),
            ( user.rate_plan > 0 ) and unsubscribe_button or None,
          ) or None,
          class_ = u"upgrade_area",
        ),

        Div(
          Div(
            Img(
              src = u"/static/images/more_room_to_stretch_out.png",
              width = u"280", height = u"29",
              alt = u"More room to stretch out",
            ),
            Ul(
              Li( u"More space for your wiki notes." ),
              Li( u"More space for your documents and files." ),
              class_ = u"upgrade_text",
            ),
            Img(
              src = u"/static/images/zero_hassle.png",
              width = u"122", height = u"29",
              alt = u"Zero hassle",
            ),
            Ul(
              Li( u"Cancel online anytime without losing access to your wiki." ),
              Li( u"60-day money-back guarantee. No questions asked." ),
              Li( u"No lock-in: Download your entire wiki anytime." ),
              class_ = u"upgrade_text",
            ),
            class_= u"upgrade_right_area",
          ),

          Div(
            Img(
              src = u"/static/images/more_collaboration.png",
              width = u"204", height = u"29",
              alt = u"More collaboration",
            ),
            P(
              Ul(
                Li( u"Invite specific people to collaborate on your wiki." ),
                Li( u"Decide who can edit and who can only view." ),
                Li( u"Invite as many people as you want. They only need free Luminotes accounts." ),
                Li( u"Revoke access with a single click." ),
                Li( u"Share only the notebooks you want to share. Keep the others private." ),
                class_ = u"upgrade_text",
              ),
            ),
            class_= u"upgrade_left_area",
          ),

          P(
            Table(
              self.fee_row( rate_plans, user, include_blank = False ),
              Tr(
                [ Td(
                  plan[ u"storage_quota_bytes" ] // MEGABYTE, " MB",
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

  def fee_row( self, rate_plans, user, include_blank = True ):
    return Tr(
      include_blank and Th( u"&nbsp;" ) or None,
      [ Th(
        plan[ u"name" ].capitalize(),
        plan[ u"fee" ] and Div(
          Span(
            u"$%s" % plan[ u"fee" ],
            Span( u"/month", class_ = u"month_text" ),
            class_ = u"price_text",
            separator = u"",
          ),
          user and user.username not in ( u"anonymous", None ) and user.rate_plan != index \
               and plan.get( u"button" ).strip() and plan.get( u"button" ) % user.object_id or None,
        ) or None,
        ( not user or user.username in ( u"anonymous", None ) ) and Div(
          A(
            Img( src = u"/static/images/sign_up_button.png", width = "76", height = "23" ),
            href = u"/sign_up?plan=%s" % index,
          ),
          class_ = u"sign_up_button_area",
        ) or None,
        class_ = u"plan_name",
      ) for ( index, plan ) in enumerate( rate_plans ) ],
    )
