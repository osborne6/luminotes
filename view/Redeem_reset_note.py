from Tags import Span, H3, P, Form, P, Div, Strong, Br, Input


class Redeem_reset_note( Span ):
  def __init__( self, password_reset_id, users ):
    Span.__init__(
      self,
      H3( u"complete your password reset" ),
      P(
        """
        Below is a list of Luminotes users matching your email address. You can reset
        the passwords of any of these users. If you just needed a username reminder and
        you already know your password, then click the login link above without performing
        a password reset.
        """
      ),
      Form(
        [ Span(
          P(
            Div( Strong( u"%s: new password" % user.username ) ),
            Input( type = u"password", name = user.object_id, size = 30, maxlength = 30, class_ = u"text_field" ),
          ),
          P(
            Div( Strong( u"%s: new password (again)" % user.username ) ),
            Input( type = u"password", name = user.object_id, size = 30, maxlength = 30, class_ = u"text_field" ),
          ),
        ) for user in users ],
        P(
          Input( type = u"hidden", id = u"password_reset_id", name = u"password_reset_id", value = password_reset_id ),
          Input(
            type = u"submit",
            name = u"reset_button",
            id = u"reset_button",
            class_ = u"button",
            value = ( len( users ) > 1 ) and u"reset passwords" or u"reset password" ),
        ),
        id = "reset_form",
        target = "/users/reset_password",
      ),
      P(
        Strong( u"tip:" ),
        u"""
        When you submit this form, you'll be redirected to the front page where you can login with
        your new password.
        """,
      ),
    )
