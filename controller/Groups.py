from Expose import expose
from Expire import strongly_expire
from Users import grab_user_id, Access_error
from model.Group import Group
from model.User import User
from view.Json import Json
from Validate import validate, Valid_string, Valid_bool, Valid_int, Validation_error
from Database import Valid_id, end_transaction


class Groups( object ):
  def __init__( self, database, users ):
    self.__database = database
    self.__users = users

  @expose( view = Json )
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    group_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def load_users( self, group_id, user_id = None ):
    """
    Return the users within the given group. This method is only available to an admin of the
    group.

    @type group_id: unicode
    @param group_id: id of group whose users to return
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: dict
    @return: {
      'group': group_info,
      'admin_users': admin_user_list,
      'other_users': non_admin_user_list,
    }
    @raise Access_error: the current user doesn't have admin membership to the given group
    @raise Validation_error: one of the arguments is invalid
    """
    if not self.__users.check_group( user_id, group_id, admin = True ):
      raise Access_error()

    group = self.__database.load( Group, group_id )

    if group is None:
      raise Access_error()

    admin_users = self.__database.select_many( User, group.sql_load_users( admin = True ) )
    other_users = self.__database.select_many( User, group.sql_load_users( admin = False ) )

    return dict(
      group = group,
      admin_users = admin_users,
      other_users = other_users,
    )
