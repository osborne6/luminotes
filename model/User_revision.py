class User_revision( object ):
  """
  A revision timestamp along with information on the user that made that revision.
  """
  def __init__( self, revision, user_id = None, username = None ):
    """
    Create a User_revision with the given timestamp and user information.

    @type revision: datetime
    @param revision: revision timestamp
    @type user_id: unicode or NoneType
    @param user_id: id of user who made this revision (optional, defaults to None)
    @type username: username of user who made this revision (optional, defaults to None)
    @rtype: User_revision
    @return: newly constructed User_revision object
    """
    self.__revision = revision
    self.__user_id = user_id
    self.__username = username

  def to_dict( self ):
    return dict(
      revision = self.__revision,
      user_id = self.__user_id,
      username = self.__username,
    )

  revision = property( lambda self: self.__revision )
  user_id = property( lambda self: self.__user_id )
  username = property( lambda self: self.__username )
