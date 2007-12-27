from Tags import Span, H3, P, A


class Redeem_invite_note( Span ):
  def __init__( self, invite, notebook ):
    title = None

    Span.__init__(
      self,
      H3( notebook.name ),
      P(
        u"You are just seconds away from viewing \"%s\"." % notebook.name,
      ),
      P(
        u"If you already have a Luminotes account, then simply ",
        A( u"login", href = u"/login?invite_id=%s" % invite.object_id, target = "_top" ),
        u" to your account."
      ),
      P(
        u"Otherwise, please ",
        A( u"sign up", href = u"/sign_up?invite_id=%s" % invite.object_id, target = "_top" ),
        u" for a free account."
      ),
    )
