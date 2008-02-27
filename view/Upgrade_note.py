from Tags import Div, Span, H3, P, A, Table, Tr, Th, Td, Br, Img


class Upgrade_note( Span ):
  def __init__( self, rate_plans, unsubscribe_button, https_url, user ):
    MEGABYTE = 1024 * 1024

    Span.__init__(
      self,
      H3( u"upgrade your wiki" ),
      P(
        """
        Use of your personal wiki is completely free. But if you upgrade your
        Luminotes account, you'll also get more storage space and powerful
        notebook sharing features so that you and your friends can all
        collaborate on your wiki notebook.
        """,
      ),
      P(
        Table(
          self.fee_row( rate_plans, user ),
          Tr(
            Td( u"included storage space", class_ = u"feature_name" ),
            [ Td(
              plan[ u"storage_quota_bytes" ] // MEGABYTE, " MB",
            ) for plan in rate_plans ],
          ),
          Tr(
            Td( u"unlimited wiki notebooks", class_ = u"feature_name" ),
            [ Td(
              Img( src = u"/static/images/check.png", width = u"20", height = u"17" ),
            ) for plan in rate_plans ],
          ),
          Tr(
            Td( u"friendly email support", class_ = u"feature_name" ),
            [ Td(
              Img( src = u"/static/images/check.png", width = u"20", height = u"17" ),
            ) for plan in rate_plans ],
          ),
          Tr(
            Td( u"multi-user collaboration", class_ = u"feature_name" ),
            [ Td(
              plan[ u"notebook_collaboration" ] and
              Img( src = u"/static/images/check.png", width = u"20", height = u"17" ) or u"&nbsp",
            ) for plan in rate_plans ],
          ),
          Tr(
            Td( u"wiki access control", class_ = u"feature_name" ),
            [ Td(
              plan[ u"notebook_collaboration" ] and
              Img( src = u"/static/images/check.png", width = u"20", height = u"17" ) or u"&nbsp",
            ) for plan in rate_plans ],
          ),
          border = u"1",
          id = u"upgrade_table",
        ),
        ( not user or not user.username ) and P(
          u"To upgrade your Luminotes account, please",
          A( u"login", href = https_url + u"/login?after_login=/upgrade", target = u"_top" ),
          u"first!",
          id = u"upgrade_login_text",
        ) or None,
        id = u"upgrade_table_area",
      ),

      user and user.username and P(
        u"You're currently subscribed to Luminotes %s." % 
        rate_plans[ user.rate_plan ][ u"name" ].capitalize(),
        ( user.rate_plan > 0 ) and unsubscribe_button or None,
      ) or None,

      H3( u"share your notebook" ),
      P(
        A(
          Img(
            src = u"/static/images/share_thumb.png",
            class_ = u"thumbnail_right",
            width = u"200",
            height = u"200",
          ),
          href = u"/static/images/share.png",
          target = u"_new",
        ),
        u"""
        Most of the time, you want to keep your personal wiki all to yourself. But
        sometimes you simply need to share your work with friends and colleagues.
        """,
      ),
      P(
        u"""
        With an upgraded Luminotes account, you'll be able to invite specific people
        to collaborate on your wiki simply by entering their email addresses. You can
        even give them full editing capabilities, so several people can contribute.
        And you can invite as many people as you want to collaborate on your wiki.
        They only need to sign up for a free Luminotes account to particpate.
        """
      ),
      H3( u"wiki access control" ),
      P(
        A(
          Img(
            src = u"/static/images/access_thumb.png",
            class_ = u"thumbnail_left",
            width = u"200",
            height = u"200",
          ),
          href = u"/static/images/access.png",
          target = u"_new",
        ),
        u"""
        With an upgraded Luminotes wiki, you'll decide exactly how much access to give
        people. Collaborators can make changes to your notebook, while viewers can
        only read your wiki. And owners have the same complete access to your notebook
        that you do. When you're done collaborating, a single click revokes a user's
        notebook access.
        """,
      ),
      P(
        u"""
        Your wiki access control works on a per-notebook basis, so you can easily
        share one notebook with your friends while keeping your other notebooks
        completely private.
        """,
      ),
      H3( u"additional storage space" ),
      P(
        u"""
        An upgraded Luminotes account gets you more than just notebook sharing
        features. You'll also be treated to way more room for your personal wiki. That
        means you'll have more space for your notes and files, and you won't have to
        worry about running out of room anytime soon.
        """,
      ),
      H3( u"no questions asked money-back guarantee" ),
      P(
        u"""
        If you upgrade your Luminotes account and later find that it's not meeting
        your needs, you can cancel online anytime. You won't have to send email or
        talk to anyone in a call center. If you do cancel, you keep all of your wiki
        notebooks and simply return to a free account.
        """,
      ),
      P(
        u"""
        Additionally, if you are unsatisfied for any reason, you have the option of
        requesting a refund within 60 days of upgrading your account. Your money will
        be returned in full without any questions.
        """
      ),
      H3( u"absolutely no lock-in" ),
      P(
        u"""
        You can download the entire contents of your wiki at any time with a single
        click, so you can rest assured that your notes won't be locked away within
        Luminotes if you ever decide to cancel. You can take all of your data and
        import it into any program that reads HTML. After all, it's your wiki.
        """,
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
        ( not user ) and P(
          u"Please",
          A( u"login", href = https_url + u"/login?after_login=/upgrade", target = u"_top" ),
          u"to upgrade your wiki!",
          id = u"upgrade_login_text",
        ) or None,
        id = u"upgrade_table_area",
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
          user and user.username and user.rate_plan != index and plan.get( u"button" ).strip() and plan.get( u"button" ) % user.object_id or None,
        ) or None,
        class_ = u"plan_name",
      ) for ( index, plan ) in enumerate( rate_plans ) ],
    )
