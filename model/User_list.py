from copy import copy
from Persistent import Persistent


class User_list( Persistent ):
  """
  A list of users.
  """
  def __init__( self, id, secondary_id = None ):
    """
    Create a list of users, and give the list the provided id.

    @type id: unicode
    @param id: id of the user list
    @type secondary_id: unicode or NoneType
    @param secondary_id: convenience id for easy access (optional)
    @rtype: User_list
    @return: newly constructed user list
    """
    Persistent.__init__( self, id, secondary_id )
    self.__users = []

  def add_user( self, user ):
    """
    Add a user to this list.

    @type user: User
    @param user: user to add
    """
    if user.object_id not in [ u.object_id for u in self.__users ]:
      self.update_revision()
      self.__users.append( user )

  def remove_user( self, user ):
    """
    Remove a user from this list.

    @type user: User
    @param user: user to remove
    """
    if user in self.__users:
      self.update_revision()
      self.__users.remove( user )

  def __set_users( self, users ):
    self.__users = users

  users = property( lambda self: copy( self.__users ), __set_users )
