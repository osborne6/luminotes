import sha
import random
from copy import copy
from Persistent import Persistent


class User( Persistent ):
  """
  A user of this application.
  """
  SALT_CHARS = [ chr( c ) for c in range( ord( "!" ), ord( "~" ) + 1 ) ]
  SALT_SIZE = 12

  def __setstate__( self, state ):
    if "_User__storage_bytes" not in state:
      state[ "_User__storage_bytes" ] = False

    self.__dict__.update( state )

  def __init__( self, id, username, password, email_address, notebooks = None ):
    """
    Create a new user with the given credentials and information.

    @type id: unicode
    @param id: id of the user
    @type username: unicode
    @param username: unique user identifier for login purposes
    @type password: unicode
    @param password: secret password for login purposes
    @type email_address: unicode
    @param email_address: a hopefully valid email address
    @type notebooks: [ Notebook ]
    @param notebooks: list of notebooks (read-only and read-write) that this user has access to
    @rtype: User
    @return: newly created user
    """
    Persistent.__init__( self, id, secondary_id = username )
    self.__salt = self.__create_salt()
    self.__password_hash = self.__hash_password( password )
    self.__email_address = email_address
    self.__notebooks = notebooks or []
    self.__storage_bytes = 0 # total storage bytes for this user's notebooks, notes, and revisions

  def __create_salt( self ):
    return "".join( [ random.choice( self.SALT_CHARS ) for i in range( self.SALT_SIZE ) ] )

  def __hash_password( self, password ):
    if password is None or len( password ) == 0:
      return None

    return sha.new( self.__salt + password ).hexdigest()

  def check_password( self, password ):
    """
    Check that the given password matches this user's password.

    @type password: unicode
    @param password: password to check
    @rtype: bool
    @return: True if the password matches
    """
    if self.__password_hash == None:
      return False

    hash = self.__hash_password( password )
    if hash == self.__password_hash:
      return True

    return False

  def has_access( self, notebook_id ):
    if notebook_id in [ notebook.object_id for notebook in self.__notebooks ]:
      return True

    # a user who has read-write access to a notebook also has access to that notebook's trash
    if notebook_id in [ notebook.trash.object_id for notebook in self.__notebooks if notebook.trash ]:
      return True

    return False

  def to_dict( self ):
    d = Persistent.to_dict( self )
    d.update( dict(
      username = self.username,
    ) )

    return d

  def __set_password( self, password ):
    self.update_revision()
    self.__salt = self.__create_salt()
    self.__password_hash = self.__hash_password( password )

  def __set_notebooks( self, notebooks ):
    self.update_revision()
    self.__notebooks = notebooks

  def __set_storage_bytes( self, storage_bytes ):
    self.update_revision()
    self.__storage_bytes = storage_bytes

  username = property( lambda self: self.secondary_id )
  email_address = property( lambda self: self.__email_address )
  password = property( None, __set_password )
  storage_bytes = property( lambda self: self.__storage_bytes, __set_storage_bytes )

  # the notebooks (read-only and read-write) that this user has access to
  notebooks = property( lambda self: copy( self.__notebooks ), __set_notebooks )
