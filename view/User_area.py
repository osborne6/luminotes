from Tags import Div, H4, A


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
        A(
          u"logout",
          href = logout_url,
          id = u"logout_link",
        ),
      ),
      id = u"user_area",
    )
