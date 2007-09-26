from Persistent import Persistent


class Password_reset( Persistent ):
  """
  A request for a password reset.
  """
  def __init__( self, id, email_address ):
    """
    Create a password reset request with the given id.

    @type id: unicode
    @param id: id of the password reset
    @type email_address: unicode
    @param email_address: where the reset confirmation was emailed
    @rtype: Password_reset
    @return: newly constructed password reset
    """
    Persistent.__init__( self, id )
    self.__email_address = email_address
    self.__redeemed = False

  def __set_redeemed( self, redeemed ):
    if redeemed != self.__redeemed:
      self.update_revision()
      self.__redeemed = redeemed

  email_address = property( lambda self: self.__email_address )
  redeemed = property( lambda self: self.__redeemed, __set_redeemed )
