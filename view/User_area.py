from Tags import Div, Span, H4, A


class User_area( Div ):
  def __init__( self, user, login_url, logout_url ):
    Div.__init__(
      self,
      ( login_url and user.username == u"anonymous" ) and Div(
        A(
          u"login",
          href = login_url,
          id = u"login_link",
        ),
      ) or Div(
        u"logged in as %s" % ( user.username or u"a guest" ),
        " | ",
        ( user.username == None ) and Span(
          A(
            u"sign up",
            href = u"/sign_up",
            title = u"Sign up for a real Luminotes account.",
          ),
          " | ",
        ) or None,
        ( user.username and user.rate_plan == 0 ) and Span(
          A(
            u"upgrade",
            href = u"/upgrade",
            title = u"Upgrade your Luminotes account.",
          ),
          " | ",
        ) or None,
        A(
          u"logout",
          href = logout_url,
          id = u"logout_link",
          title = u"Sign out of your account."
        ),
      ),
      id = u"user_area",
    )
