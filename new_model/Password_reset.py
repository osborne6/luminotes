from Persistent import Persistent, quote


class Password_reset( Persistent ):
  """
  A request for a password reset.
  """
  def __init__( self, object_id, email_address = None, redeemed = False ):
    """
    Create a password reset request with the given id.

    @type object_id: unicode
    @param object_id: id of the password reset
    @type email_address: unicode
    @param email_address: where the reset confirmation was emailed
    @type redeemed: bool or NoneType
    @param redeemed: whether this password reset has been redeemed yet (optional, defaults to False)
    @rtype: Password_reset
    @return: newly constructed password reset
    """
    Persistent.__init__( self, object_id )
    self.__email_address = email_address
    self.__redeemed = redeemed

  @staticmethod
  def sql_load( object_id, revision = None ):
    # password resets don't track revisions
    if revision:
      raise NotImplementedError()

    return "select * from password_reset where id = %s;" % quote( object_id )

  @staticmethod
  def sql_id_exists( object_id, revision = None ):
    if revision:
      raise NotImplementedError()

    return "select id from password_reset where id = %s;" % quote( object_id )

  def sql_exists( self ):
    return Password_reset.sql_id_exists( self.object_id )

  def sql_create( self ):
    return "insert into password_reset ( id, email_address, redeemed ) values ( %s, %s, %s );" % \
    ( quote( self.object_id ), quote( self.__email_address ), quote( self.__redeemed and "t" or "f" ) )

  def sql_update( self ):
    return "update password_reset set redeemed = %s where id = %s;" % \
    ( quote( self.__redeemed and "t" or "f" ), quote( self.object_id ) )

  def __set_redeemed( self, redeemed ):
    if redeemed != self.__redeemed:
      self.update_revision()
      self.__redeemed = redeemed

  email_address = property( lambda self: self.__email_address )
  redeemed = property( lambda self: self.__redeemed, __set_redeemed )
