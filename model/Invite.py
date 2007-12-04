from Persistent import Persistent, quote


class Invite( Persistent ):
  """
  An invitiation to view or edit a notebook.
  """
  def __init__( self, object_id, revision = None, from_user_id = None, notebook_id = None,
                email_address = None, read_write = False, owner = False, redeemed_user_id = None ):
    """
    Create an invitation with the given id.

    @type object_id: unicode
    @param object_id: id of the invitation
    @type revision: datetime or NoneType
    @param revision: revision timestamp of the object (optional, defaults to now)
    @type from_user_id: unicode or NoneType
    @param from_user_id: id of the user who sent the invite (optional)
    @type notebook_id: unicode or NoneType
    @param notebook_id: id of the notebook that the invitation is for
    @type email_address: unicode or NoneType
    @param email_address: where the invitation was emailed (optional)
    @type read_write: bool or NoneType
    @param read_write: whether the invitation is for read-write access (optional, defaults to False)
    @type owner: bool or NoneType
    @param owner: whether the invitation is for owner-level access (optional, defaults to False)
    @type redeemed_user_id: unicode or NoneType
    @param redeemed_user_id: id of the user who has redeemed this invitation, if any (optional)
    @rtype: Invite
    @return: newly constructed notebook invitation
    """
    Persistent.__init__( self, object_id, revision )
    self.__from_user_id = from_user_id
    self.__notebook_id = notebook_id
    self.__email_address = email_address
    self.__read_write = read_write
    self.__owner = owner
    self.__redeemed_user_id = redeemed_user_id

  @staticmethod
  def create( object_id, from_user_id = None, notebook_id = None, email_address = None, read_write = False, owner = False ):
    """
    Convenience constructor for creating a new invitation.

    @type object_id: unicode
    @param object_id: id of the invitation
    @type from_user_id: unicode or NoneType
    @param from_user_id: id of the user who sent the invite (optional)
    @type notebook_id: unicode or NoneType
    @param notebook_id: id of the notebook that the invitation is for
    @type email_address: unicode or NoneType
    @param email_address: where the invitation was emailed (optional)
    @type read_write: bool or NoneType
    @param read_write: whether the invitation is for read-write access (optional, defaults to False)
    @type owner: bool or NoneType
    @param owner: whether the invitation is for owner-level access (optional, defaults to False)
    @rtype: Invite
    @return: newly constructed notebook invitation
    """
    return Invite( object_id, from_user_id = from_user_id, notebook_id = notebook_id,
                   email_address = email_address, read_write = read_write, owner = owner )

  @staticmethod
  def sql_load( object_id, revision = None ):
    # password resets don't store old revisions
    if revision:
      raise NotImplementedError()

    return "select id, revision, from_user_id, notebook_id, email_address, read_write, owner, redeemed_user_id from invite where id = %s;" % quote( object_id )

  @staticmethod
  def sql_id_exists( object_id, revision = None ):
    if revision:
      raise NotImplementedError()

    return "select id from invite where id = %s;" % quote( object_id )

  def sql_exists( self ):
    return Invite.sql_id_exists( self.object_id )

  def sql_create( self ):
    return "insert into invite ( id, revision, from_user_id, notebook_id, email_address, read_write, owner, redeemed_user_id ) values ( %s, %s, %s, %s, %s, %s, %s, %s );" % \
    ( quote( self.object_id ), quote( self.revision ), quote( self.__from_user_id ), quote( self.__notebook_id ),
      quote( self.__email_address ), quote( self.__read_write and "t" or "f" ), quote( self.__owner and "t" or "f" ),
      quote( self.__redeemed_user_id ) )

  def sql_update( self ):
    return "update invite set revision = %s, from_user_id = %s, notebook_id = %s, email_address = %s, read_write = %s, owner = %s, redeemed_user_id = %s where id = %s;" % \
    ( quote( self.object_id ), quote( self.revision ), quote( self.__from_user_id ), quote( self.__notebook_id ),
      quote( self.__email_address ), quote( self.__read_write and "t" or "f" ), quote( self.__owner and "t" or "f" ),
      quote( self.__redeemed_user_id ) )

  def __set_redeemed_user_id( self, redeemed_user_id ):
    if redeemed_user_id != self.__redeemed_user_id:
      self.update_revision()
      self.__redeemed_user_id = redeemed_user_id

  from_user_id = property( lambda self: self.__from_user_id )
  notebook_id = property( lambda self: self.__notebook_id )
  email_address = property( lambda self: self.__email_address )
  read_write = property( lambda self: self.__read_write )
  owner = property( lambda self: self.__owner )
  redeemed_user_id = property( lambda self: self.__redeemed_user_id, __set_redeemed_user_id )
