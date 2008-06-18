import re
import urllib
import urllib2
import cherrypy
from pytz import utc
from datetime import datetime, timedelta
from model.User import User
from model.Group import Group
from model.Notebook import Notebook
from model.Note import Note
from model.Password_reset import Password_reset
from model.Invite import Invite
from Expose import expose
from Validate import validate, Valid_string, Valid_bool, Valid_int, Validation_error
from Database import Valid_id, end_transaction
from Expire import strongly_expire
from view.Json import Json
from view.Main_page import Main_page
from view.Redeem_reset_note import Redeem_reset_note
from view.Redeem_invite_note import Redeem_invite_note
from view.Blank_page import Blank_page
from view.Thanks_note import Thanks_note
from view.Thanks_error_note import Thanks_error_note
from view.Processing_note import Processing_note
from view.Form_submit_page import Form_submit_page


USERNAME_PATTERN = re.compile( "^[a-zA-Z0-9]+$" )
EMAIL_ADDRESS_PATTERN = re.compile( "^[\w.%+-]+@[\w-]+(\.[\w-]+)+$" )
EMBEDDED_EMAIL_ADDRESS_PATTERN = re.compile( "(?:^|[\s,<])([\w.%+-]+@[\w-]+(?:\.[\w-]+)+)(?:[\s,>]|$)" )
WHITESPACE_OR_COMMA_PATTERN = re.compile( "[\s,]" )


def valid_username( username ):
  if USERNAME_PATTERN.search( username ) is None:
    raise ValueError()

  return username

valid_username.message = u"can only contain letters and digits"


def valid_email_address( email_address ):
  if email_address == "" or EMAIL_ADDRESS_PATTERN.search( email_address ) is None:
    raise ValueError()

  return email_address


class Signup_error( Exception ):
  def __init__( self, message ):
    Exception.__init__( self, message )
    self.__message = message

  def to_dict( self ):
    return dict(
      error = self.__message
    )


class Authentication_error( Exception ):
  def __init__( self, message ):
    Exception.__init__( self, message )
    self.__message = message

  def to_dict( self ):
    return dict(
      error = self.__message
    )


class Password_reset_error( Exception ):
  def __init__( self, message ):
    Exception.__init__( self, message )
    self.__message = message

  def to_dict( self ):
    return dict(
      error = self.__message
    )


class Invite_error( Exception ):
  def __init__( self, message ):
    Exception.__init__( self, message )
    self.__message = message

  def to_dict( self ):
    return dict(
      error = self.__message
    )


class Access_error( Exception ):
  def __init__( self, message = None ):
    if message is None:
      message = u"Sorry, you don't have access to do that. Please make sure you're logged in as the correct user."

    Exception.__init__( self, message )
    self.__message = message

  def to_dict( self ):
    return dict(
      error = self.__message
    )


class Payment_error( Exception ):
  def __init__( self, message, params ):
    message += "\n" + unicode( params )
    Exception.__init__( self, message )
    self.__message = message

  def to_dict( self ):
    return dict(
      error = self.__message
    )


def grab_user_id( function ):
  """
  A decorator to grab the current logged in user id from the cherrypy session and pass it as a
  user_id argument to the decorated function. This decorator must be used from within the main
  cherrypy request thread.
  """
  def get_id( *args, **kwargs ):
    arg_names = list( function.func_code.co_varnames )
    if "user_id" in arg_names:
      arg_index = arg_names.index( "user_id" )
      args = list( args )
      args[ arg_index - 1 ] = cherrypy.session.get( "user_id" )
    else:
      kwargs[ "user_id" ] = cherrypy.session.get( "user_id" )

    try:
      return function( *args, **kwargs )
    except Access_error:
      # if there was an Access_error, and the user isn't logged in, and this is an HTTP GET request,
      # redirect to the login page
      if cherrypy.session.get( "user_id" ) is None and cherrypy.request.method == "GET":
        original_path = cherrypy.request.path + \
          ( cherrypy.request.query_string and u"?%s" % cherrypy.request.query_string or "" )
        raise cherrypy.HTTPRedirect( u"/login?after_login=%s" % urllib.quote( original_path ) )
      else:
        raise
  
  return get_id


def update_auth( function ):
  """
  Based on the return value of the decorated function, update the current session's authentication
  status. This decorator must be used from within the main cherrypy request thread.

  If the return value of the decorated function (which is expected to be a dictionary) contains an
  "authenticated" key with a User value, then mark the user as logged in. If the return value of the
  decorated function contains a "deauthenticated" key with any value, then mark the user as logged
  out.
  """
  def handle_result( *args, **kwargs ):
    result = function( *args, **kwargs )

    # peek in the function's return value to see if we should tweak authentication status
    user = result.get( "authenticated" )
    if user:
      result.pop( "authenticated", None )
      cherrypy.session[ u"user_id" ] = user.object_id
      cherrypy.session[ u"username" ] = user.username

    if result.get( "deauthenticated" ):
      result.pop( "deauthenticated", None )
      cherrypy.session.pop( u"user_id", None )
      cherrypy.session.pop( u"username", None )

    return result

  return handle_result


class Users( object ):
  """
  Controller for dealing with users, corresponding to the "/users" URL.
  """
  def __init__( self, database, http_url, https_url, support_email, payment_email, rate_plans ):
    """
    Create a new Users object.

    @type database: controller.Database
    @param database: database that users are stored in
    @type http_url: unicode
    @param http_url: base URL to use for non-SSL http requests, or an empty string
    @type https_url: unicode
    @param https_url: base URL to use for SSL http requests, or an empty string
    @type support_email: unicode
    @param support_email: email address for support requests
    @type payment_email: unicode
    @param payment_email: email address for payment
    @type rate_plans: [ { "name": unicode, "storage_quota_bytes": int } ]
    @param rate_plans: list of configured rate plans
    @rtype: Users
    @return: newly constructed Users
    """
    self.__database = database
    self.__http_url = http_url
    self.__https_url = https_url
    self.__support_email = support_email
    self.__payment_email = payment_email
    self.__rate_plans = rate_plans

  def __create_user( self, username, password, password_repeat, email_address, initial_rate_plan = None ):
    """
    Create a new User based on the given information. Start that user with their own Notebook and a
    "welcome to your wiki" Note. This method does not commit the transaction to the database.

    @type username: unicode (alphanumeric only)
    @param username: username to use for this new user
    @type password: unicode
    @param password: password to use
    @type password_repeat: unicode
    @param password_repeat: password to use, again
    @type email_address: unicode
    @param email_address: user's email address
    @type initial_rate_plan: int or NoneType
    @param initial_rate_plan: index of rate plan to start the user with before they even subscribe
                              (defaults to None)
    @type user: ( model.User, model.Notebook )
    @parm user: ( newly created user, newly created notebook )
    @raise Signup_error: passwords don't match or the username is unavailable
    @raise Validation_error: the email address is invalid
    """
    if password != password_repeat:
      raise Signup_error( u"The passwords you entered do not match. Please try again." )

    user = self.__database.select_one( User, User.sql_load_by_username( username ) )

    if user is not None:
      raise Signup_error( u"Sorry, that username is not available. Please try something else." )

    if len( email_address ) > 0:
      try:
        email_address = valid_email_address( email_address )
      except ValueError:
        raise Validation_error( "email_address", email_address, valid_email_address )

    # create a notebook for this user, along with a trash for that notebook
    trash_id = self.__database.next_id( Notebook, commit = False )
    trash = Notebook.create( trash_id, u"trash" )
    self.__database.save( trash, commit = False )

    notebook_id = self.__database.next_id( Notebook, commit = False )
    notebook = Notebook.create( notebook_id, u"my notebook", trash_id )
    self.__database.save( notebook, commit = False )

    # create a startup note for this user's notebook
    note_id = self.__database.next_id( Note, commit = False )
    note_contents = file( u"static/html/welcome to your wiki.html" ).read()
    note = Note.create( note_id, note_contents, notebook_id, startup = True, rank = 0 )
    self.__database.save( note, commit = False )

    # actually create the new user
    user_id = self.__database.next_id( User, commit = False )
    user = User.create( user_id, username, password, email_address, rate_plan = initial_rate_plan )
    self.__database.save( user, commit = False )

    # record the fact that the new user has access to their new notebook
    self.__database.execute( user.sql_save_notebook( notebook_id, read_write = True, owner = True, rank = 0 ), commit = False )
    self.__database.execute( user.sql_save_notebook( trash_id, read_write = True, owner = True ), commit = False )

    return ( user, notebook )

  @expose( view = Json )
  @end_transaction
  @update_auth
  @validate(
    username = ( Valid_string( min = 1, max = 30 ), valid_username ),
    password = Valid_string( min = 1, max = 30 ),
    password_repeat = Valid_string( min = 1, max = 30 ),
    email_address = ( Valid_string( min = 0, max = 60 ) ),
    signup_button = unicode,
    invite_id = Valid_id( none_okay = True ),
    rate_plan = Valid_int( none_okay = True ),
    yearly = Valid_bool( none_okay = True ),
  )
  def signup( self, username, password, password_repeat, email_address, signup_button, invite_id = None, rate_plan = None, yearly = False ):
    """
    Create a new User based on the given information. For convenience, login the newly created user
    as well.

    @type username: unicode (alphanumeric only)
    @param username: username to use for this new user
    @type password: unicode
    @param password: password to use
    @type password_repeat: unicode
    @param password_repeat: password to use, again
    @type email_address: unicode
    @param email_address: user's email address
    @type signup_button: unicode
    @param signup_button: ignored
    @type invite_id: unicode
    @param invite_id: id of invite to redeem upon signup (optional)
    @type rate_plan: int
    @param rate_plan: index of rate plan to signup for (optional). if greater than zero, redirect
                      to PayPal subscribe page after signup
    @type yearly: bool
    @param yearly: True for a yearly rate plan, False for monthly (optional, defaults to False )
    @rtype: json dict
    @return: { 'redirect': url, 'authenticated': userdict }
    @raise Signup_error: passwords don't match or the username is unavailable
    @raise Validation_error: one of the arguments is invalid
    """
    ( user, notebook ) = self.__create_user( username, password, password_repeat, email_address )
    self.__database.commit()

    # if there's an invite_id, then redeem that invite and redirect to the invite's notebook
    if invite_id:
      invite = self.__database.load( Invite, invite_id )
      if not invite:
        raise Signup_error( u"The invite is unknown." )

      self.convert_invite_to_access( invite, user.object_id )
      redirect = u"/notebooks/%s" % invite.notebook_id
    # if there's a requested rate plan, then redirect to the PayPal subscribe page
    elif rate_plan and rate_plan > 0:
      redirect = u"/users/subscribe?rate_plan=%s&yearly=%s" % ( rate_plan, yearly )
    # otherwise, just redirect to the newly created notebook
    else:
      redirect = u"/notebooks/%s" % notebook.object_id

    return dict(
      redirect = redirect,
      authenticated = user,
    )

  @expose( view = Json )
  @end_transaction
  @grab_user_id
  @validate(
    group_id = Valid_id(),
    username = ( Valid_string( min = 1, max = 30 ), valid_username ),
    password = Valid_string( min = 1, max = 30 ),
    password_repeat = Valid_string( min = 1, max = 30 ),
    email_address = ( Valid_string( min = 0, max = 60 ) ),
    create_user_button = unicode,
    user_id = Valid_id( none_okay = True )
  )
  def signup_group_member( self, group_id, username, password, password_repeat, email_address, create_user_button, user_id ):
    """
    Create a new User in a particular group based on the given information. Start that user with
    their own Notebook and a "welcome to your wiki" Note. This method is only available to a user
    with admin access to the group.

    @type group_id: unicode
    @param group_id: id of the group to which the new user should be added
    @type username: unicode (alphanumeric only)
    @param username: username to use for this new user
    @type password: unicode
    @param password: password to use
    @type password_repeat: unicode
    @param password_repeat: password to use, again
    @type email_address: unicode
    @param email_address: user's email address
    @type create_user_button: unicode
    @param create_user_button: ignored
    @type user_id: unicode
    @param user_id: id of current logged-in user
    @rtype: json dict
    @return: { 'message': message }
    @raise Signup_error: passwords don't match or the username is unavailable
    @raise Validation_error: one of the arguments is invalid
    @raise Access_error: the current user doesn't have admin membership to the given group
    """
    if not self.check_group( user_id, group_id, admin = True ):
      raise Access_error()

    user = self.__database.load( User, user_id )
    if not user:
      raise Access_error()

    if user.rate_plan < 0 or user.rate_plan >= len( self.__rate_plans ):
      raise Access_error()

    plan = self.__rate_plans[ user.rate_plan ]

    if not plan.get( u"user_admin" ):
      raise Access_error()

    # the current user's rate plan has a maximum number of included users. make sure we're not
    # exceeding that number
    included_users_count = plan.get( u"included_users" )
    if not included_users_count:
      raise Access_error()

    group = self.__database.load( Group, group_id )
    if not group:
      raise Access_error() 

    # TODO: once multiple groups per account are supported, this needs to count all users in all
    # groups of the current admin user
    group_users = self.__database.select_many( User, group.sql_load_users() )
    if len( group_users ) >= included_users_count:
      raise Signup_error( 'Your current rate plan includes a maximum of %s users. Please upgrade your account for additional users.' % included_users_count )

    # create a new user with the same rate plan as the currently logged-in user
    ( created_user, notebook ) = self.__create_user(
      username,
      password,
      password_repeat,
      email_address,
      initial_rate_plan = user.rate_plan,
    )

    # add the new user to the group
    self.__database.execute( created_user.sql_save_group( group_id, admin = False ), commit = False )
    self.__database.commit()

    return dict(
      message = u"A new group member has been created."
    )

  @expose( view = Form_submit_page )
  @grab_user_id
  @validate(
    rate_plan = Valid_int(),
    yearly = Valid_bool( none_okay = True ),
    user_id = Valid_id(),
  )
  def subscribe( self, rate_plan, yearly = False, user_id = None ):
    """
    Submit a subscription form to PayPal, allowing the user to subscribe to the given rate plan.

    @type rate_plan: int
    @param rate_plan: index of rate plan to subscribe to
    @type yearly: bool
    @param yearly: True for a yearly rate plan, False for monthly (optional, defaults to False )
    @type user_id: unicode
    @param user_id: id of current logged-in user
    @rtype: dict
    @return: { 'form': subscription_form_html }
    @raise Signup_error: invalid rate plan, no logged-in user, or missing subscribe button
    """
    if rate_plan == 0 or rate_plan >= len( self.__rate_plans ):
      raise Signup_error( u"The rate plan is invalid." )

    plan = self.__rate_plans[ rate_plan ]
    if yearly:
      button = plan.get( u"yearly_button" )
    else:
      button = plan.get( u"button" )
    if not button or not button.strip():
      raise Signup_error(
        u"Sorry, that rate plan is not configured for subscriptions. Please contact %s." % \
        ( self.__support_email or u"support" )
      )

    return dict(
      form = button % user_id,
    )

  @expose()
  @end_transaction
  @grab_user_id
  @update_auth
  def demo( self, user_id = None ):
    """
    Create a new guest User for purposes of the demo. Start that user with their own Notebook and
    "welcome to your wiki" and "this is a demo" notes. For convenience, login the newly created
    user as well.

    If the user is already logged in as a guest user when calling this function, then skip
    creating a new user and notebook, and just redirect to the guest user's existing notebook.

    @type user_id: unicode
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: { 'redirect': url, 'authenticated': userdict }
    """
    # if the user is already logged in as a guest, then just redirect to their existing demo
    # notebook
    if user_id:
      user = self.__database.load( User, user_id )
      first_notebook = self.__database.select_one( Notebook, user.sql_load_notebooks( parents_only = True, undeleted_only = True ) )
      if user.username is None and first_notebook:
        redirect = u"/notebooks/%s" % first_notebook.object_id
        return dict( redirect = redirect )

    # create a demo notebook for this user, along with a trash for that notebook
    trash_id = self.__database.next_id( Notebook, commit = False )
    trash = Notebook.create( trash_id, u"trash" )
    self.__database.save( trash, commit = False )

    notebook_id = self.__database.next_id( Notebook, commit = False )
    notebook = Notebook.create( notebook_id, u"my notebook", trash_id )
    self.__database.save( notebook, commit = False )

    # create startup notes for this user's notebook
    note_id = self.__database.next_id( Note, commit = False )
    note_contents = file( u"static/html/this is a demo.html" ).read()
    note = Note.create( note_id, note_contents, notebook_id, startup = True, rank = 0 )
    self.__database.save( note, commit = False )

    note_id = self.__database.next_id( Note, commit = False )
    note_contents = file( u"static/html/welcome to your wiki.html" ).read()
    note = Note.create( note_id, note_contents, notebook_id, startup = True, rank = 1 )
    self.__database.save( note, commit = False )

    # actually create the new user
    user_id = self.__database.next_id( User, commit = False )
    user = User.create( user_id, username = None, password = None, email_address = None )
    self.__database.save( user, commit = False )

    # record the fact that the new user has access to their new notebook
    self.__database.execute( user.sql_save_notebook( notebook_id, read_write = True, owner = True, rank = 0 ), commit = False )
    self.__database.execute( user.sql_save_notebook( trash_id, read_write = True, owner = True ), commit = False )
    self.__database.commit()

    redirect = u"/notebooks/%s" % notebook.object_id

    return dict(
      redirect = redirect,
      authenticated = user,
    )

  @expose( view = Json )
  @end_transaction
  @update_auth
  @validate(
    username = ( Valid_string( min = 1, max = 30 ), valid_username ),
    password = Valid_string( min = 1, max = 30 ),
    login_button = unicode,
    invite_id = Valid_id( none_okay = True ),
    after_login = Valid_string( min = 0, max = 1000 ),
  )
  def login( self, username, password, login_button, invite_id = None, after_login = None ):
    """
    Attempt to authenticate the user. If successful, associate the given user with the current
    session.

    @type username: unicode (alphanumeric only)
    @param username: username to login
    @type password: unicode
    @param password: the user's password
    @type invite_id: unicode
    @param invite_id: id of invite to redeem upon login (optional)
    @type after_login: unicode
    @param after_login: URL to redirect to after login (optional, must start with "/")
    @rtype: json dict
    @return: { 'redirect': url, 'authenticated': userdict }
    @raise Authentication_error: invalid username or password
    @raise Validation_error: one of the arguments is invalid
    """
    user = self.__database.select_one( User, User.sql_load_by_username( username ) )

    if user is None or user.check_password( password ) is False:
      raise Authentication_error( u"Invalid username or password." )

    first_notebook = self.__database.select_one( Notebook, user.sql_load_notebooks( parents_only = True, undeleted_only = True ) )

    # if there's an invite_id, then redeem that invite and redirect to the invite's notebook
    if invite_id:
      invite = self.__database.load( Invite, invite_id )
      if not invite:
        raise Authentication_error( u"The invite is unknown." )

      self.convert_invite_to_access( invite, user.object_id )
      redirect = u"/notebooks/%s" % invite.notebook_id
    # if there's an after_login URL, redirect to it
    elif after_login and after_login.startswith( "/" ):
      redirect = after_login
    # otherwise, just redirect to the user's first notebook (if any)
    elif first_notebook:
      redirect = u"/notebooks/%s" % first_notebook.object_id
    else:
      redirect = u"/"

    return dict(
      redirect = redirect,
      authenticated = user,
    )

  @expose()
  @end_transaction
  @update_auth
  def logout( self ):
    """
    Deauthenticate the user and log them out of their current session.

    @rtype: dict
    @return: { 'redirect': url, 'deauthenticated': True }
    """
    return dict(
      redirect = self.__http_url + u"/",
      deauthenticated = True,
    )

  def current( self, user_id ):
    """
    Return information on the currently logged-in user. If not logged in, default to the anonymous
    user.

    @type user_id: unicode
    @param user_id: id of current logged-in user (if any)
    @rtype: json dict
    @return: {
      'user': user or None,
      'notebooks': notebookslist,
      'login_url': url,
      'logout_url': url,
      'rate_plan': rateplandict,
      'groups': groups,
    }
    @raise Validation_error: one of the arguments is invalid
    @raise Access_error: user_id or anonymous user unknown
    """
    # if there's no logged-in user, default to the anonymous user
    anonymous = self.__database.select_one( User, User.sql_load_by_username( u"anonymous" ), use_cache = True )
    if user_id:
      user = self.__database.load( User, user_id )
    else:
      user = anonymous

    if not user or not anonymous:
      raise Access_error()

    user.group_storage_bytes = self.calculate_group_storage( user )

    # in addition to this user's own notebooks, add to that list the anonymous user's notebooks
    login_url = None
    anon_notebooks = self.__database.select_many( Notebook, anonymous.sql_load_notebooks( undeleted_only = True ) )

    if user_id and user_id != anonymous.object_id:
      notebooks = self.__database.select_many( Notebook, user.sql_load_notebooks() )
      groups = self.__database.select_many( Group, user.sql_load_groups() )
    # if the user is not logged in, return a login URL
    else:
      notebooks = []
      groups = []
      if len( anon_notebooks ) > 0 and anon_notebooks[ 0 ]:
        main_notebook = anon_notebooks[ 0 ]
        login_note = self.__database.select_one( Note, main_notebook.sql_load_note_by_title( u"login" ) )
        if login_note:
          login_url = "%s/notebooks/%s?note_id=%s" % ( self.__https_url, main_notebook.object_id, login_note.object_id )

    return dict(
      user = user,
      notebooks = notebooks + anon_notebooks,
      login_url = login_url,
      logout_url = self.__https_url + u"/users/logout",
      rate_plan = ( user.rate_plan < len( self.__rate_plans ) ) and self.__rate_plans[ user.rate_plan ] or {},
      groups = groups,
    )

  def calculate_storage( self, user ):
    """
    Calculate total storage utilization for all notes of the given user, including storage for all
    past revisions.

    @type user: User
    @param user: user for which to calculate storage utilization
    @rtype: int
    @return: total bytes used for storage
    """
    return sum( self.__database.select_one( tuple, user.sql_calculate_storage() ), 0 )

  def calculate_group_storage( self, user ):
    """
    Calculate total storage utilization for all groups that the given user is a member of.

    @type user: User
    @param user: user for which to calculate storage utilization
    @rtype: int
    @return: total bytes used for group storage
    """
    return sum( self.__database.select_one( tuple, user.sql_calculate_group_storage() ), 0 )

  def update_storage( self, user_id, commit = True ):
    """
    Calculate and record total storage utilization for the given user.

    @type user_id: unicode
    @param user_id: id of user for which to calculate storage utilization
    @type commit: bool
    @param commit: True to automatically commit after the update
    @rtype: model.User
    @return: object of the user corresponding to user_id
    """
    user = self.__database.load( User, user_id )

    if user:
      user.storage_bytes = self.calculate_storage( user )
      self.__database.save( user, commit )

    return user

  def check_access( self, user_id, notebook_id, read_write = False, owner = False ):
    """
    Determine whether the given user has access to the given notebook.

    @type user_id: unicode
    @param user_id: id of user whose access to check
    @type notebook_id: unicode
    @param notebook_id: id of notebook to check access for
    @type read_write: bool
    @param read_write: True if read-write access is being checked, False if read-only access (defaults to False)
    @type owner: bool
    @param owner: True if owner-level access is being checked (defaults to False)
    @rtype: bool
    @return: True if the user has access
    """
    anonymous = self.__database.select_one( User, User.sql_load_by_username( u"anonymous" ), use_cache = True )

    if self.__database.select_one( bool, anonymous.sql_has_access( notebook_id, read_write, owner ) ):
      return True

    if user_id:
      # check if the given user has access to this notebook
      user = self.__database.load( User, user_id )

      if user and self.__database.select_one( bool, user.sql_has_access( notebook_id, read_write, owner ) ):
        return True

    return False

  def check_group( self, user_id, group_id, admin = False ):
    """
    Determine whether the given user has membership to the given group.

    @type user_id: unicode
    @param user_id: id of user whose membership to check
    @type group_id: unicode
    @param group_id: id of group to check membership in
    @type admin: bool
    @param admin: True if admin-level membership is being checked (defaults to False)
    @rtype: bool
    @return: True if the user has membership
    """
    # check if the given user has access to this notebook
    user = self.__database.load( User, user_id )

    if user and self.__database.select_one( bool, user.sql_in_group( group_id, admin ) ):
      return True

    return False

  @expose( view = Json )
  @end_transaction
  @grab_user_id
  @validate(
    user_id_to_remove = Valid_id(),
    group_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def remove_group( self, user_id_to_remove, group_id, user_id = None ):
    """
    Remove a user's membership from the given group. For now, this also sets them to the lowest
    rate plan.

    @type user_id_to_remove: unicode
    @param user_id_to_remove: id of the user to remove from the group
    @type group_id: unicode
    @param group_id: id of the group to remove membership from
    @type user_id: unicode
    @param user_id: id of current logged-in user (if any)
    @raise Validation_error: one of the arguments is invalid
    @raise Access_error: the current user doesn't have admin membership to the given group
    """
    if not self.check_group( user_id, group_id, admin = True ):
      raise Access_error()

    user = self.__database.load( User, user_id_to_remove )
    if not user:
      raise Access_error()

    self.__database.execute( user.sql_remove_group( group_id ) )

    # setting the user's rate plan to 0 upon group removal prevents a group admin from creating
    # an unlimited number of users with high-end rate plans
    user.rate_plan = 0
    self.__database.save( user )

    return dict(
      message = u"Group membership for %s has been revoked." % user.username,
    )

  @expose( view = Json )
  @end_transaction
  @validate(
    email_address = ( Valid_string( min = 1, max = 60 ), valid_email_address ),
    send_reset_button = unicode,
  )
  def send_reset( self, email_address, send_reset_button ):
    """
    Send a password reset email to the given email address.

    @type email_address: unicode
    @param email_address: an existing user's email address
    @type send_reset_button: unicode
    @param send_reset_button: ignored
    @rtype: json dict
    @return: { 'message': message }
    @raise Password_reset_error: an error occured when sending the password reset email
    @raise Validation_error: one of the arguments is invalid
    """
    import smtplib
    from email import Message

    # check whether there are actually any users with the given email address
    users = self.__database.select_many( User, User.sql_load_by_email_address( email_address ) )

    if len( users ) == 0:
      raise Password_reset_error( u"There are no Luminotes users with the email address %s" % email_address )

    # record the sending of this reset email
    password_reset_id = self.__database.next_id( Password_reset, commit = False )
    password_reset = Password_reset.create( password_reset_id, email_address )
    self.__database.save( password_reset )

    # create an email message with a unique link
    message = Message.Message()
    message[ u"From" ] = u"Luminotes support <%s>" % self.__support_email
    message[ u"To" ] = email_address
    message[ u"Subject" ] = u"Luminotes password reset"
    message.set_payload(
      u"Someone has requested a password reset for a Luminotes user with your email\n" +
      u"address. If this someone is you, please visit the following link for a\n" +
      u"username reminder or a password reset:\n\n" +
      u"%s/r/%s\n\n" % ( self.__https_url or self.__http_url, password_reset.object_id ) +
      u"This link will expire in 24 hours.\n\n" +
      u"Thanks!"
    )

    # send the message out through localhost's smtp server
    server = smtplib.SMTP()
    server.connect()
    server.sendmail( message[ u"From" ], [ email_address ], message.as_string() )
    server.quit()

    return dict(
      message = u"Please check your inbox. A password reset email has been sent to %s" % email_address,
    )

  @expose( view = Main_page )
  @strongly_expire
  @end_transaction
  @validate(
    password_reset_id = Valid_id(),
  )
  def redeem_reset( self, password_reset_id ):
    """
    Provide the information necessary to display the web site's main page along with a dynamically
    generated "complete your password reset" note.

    @type password_reset_id: unicode
    @param password_reset_id: id of model.Password_reset to redeem
    @rtype: unicode
    @return: rendered HTML page
    @raise Password_reset_error: an error occured when redeeming the password reset, such as an expired link
    @raise Validation_error: one of the arguments is invalid
    """
    anonymous = self.__database.select_one( User, User.sql_load_by_username( u"anonymous" ), use_cache = True )
    if anonymous:
      main_notebook = self.__database.select_one( Notebook, anonymous.sql_load_notebooks( undeleted_only = True ) )

    if not anonymous or not main_notebook:
      raise Password_reset_error( "There was an error when completing your password reset. Please contact %s." % self.__support_email )

    password_reset = self.__database.load( Password_reset, password_reset_id )

    if not password_reset or datetime.now( tz = utc ) - password_reset.revision > timedelta( hours = 25 ):
      raise Password_reset_error( "Your password reset link has expired. Please request a new password reset email." )

    if password_reset.redeemed:
      raise Password_reset_error( "Your password has already been reset. Please request a new password reset email." )

    # find the user(s) with the email address from the password reset request
    matching_users = self.__database.select_many( User, User.sql_load_by_email_address( password_reset.email_address ) )

    if len( matching_users ) == 0:
      raise Password_reset_error( u"There are no Luminotes users with the email address %s" % password_reset.email_address )

    result = self.current( anonymous.object_id )
    result[ "notebook" ] = main_notebook
    result[ "startup_notes" ] = self.__database.select_many( Note, main_notebook.sql_load_startup_notes() )
    result[ "total_notes_count" ] = self.__database.select_one( Note, main_notebook.sql_count_notes(), use_cache = True )
    result[ "note_read_write" ] = False
    result[ "notes" ] = [ Note.create(
      object_id = u"password_reset",
      contents = unicode( Redeem_reset_note( password_reset_id, matching_users ) ),
      notebook_id = main_notebook.object_id,
    ) ]
    result[ "invites" ] = []

    return result

  @expose( view = Json )
  @end_transaction
  def reset_password( self, password_reset_id, reset_button, **new_passwords ):
    """
    Reset all the users with the provided passwords.

    @type password_reset_id: unicode
    @param password_reset_id: id of model.Password_reset to use
    @type reset_button: unicode
    @param reset_button: return
    @type new_passwords: { userid: [ newpassword, newpasswordrepeat ] }
    @param new_passwords: map of user id to new passwords or empty strings
    @rtype: json dict
    @return: { 'redirect': '/' }
    @raise Password_reset_error: an error occured when resetting the passwords, such as an expired link
    """
    try:
      id_validator = Valid_id()
      id_validator( password_reset_id )
    except ValueError:
      raise Validation_error( "password_reset_id", password_reset_id, id_validator, "is not a valid id" )

    password_reset = self.__database.load( Password_reset, password_reset_id )

    if not password_reset or datetime.now( tz = utc ) - password_reset.revision > timedelta( hours = 25 ):
      raise Password_reset_error( "Your password reset link has expired. Please request a new password reset email." )

    if password_reset.redeemed:
      raise Password_reset_error( "Your password has already been reset. Please request a new password reset email." )

    matching_users = self.__database.select_many( User, User.sql_load_by_email_address( password_reset.email_address ) )
    allowed_user_ids = [ user.object_id for user in matching_users ]

    # reset any passwords that are non-blank
    at_least_one_reset = False
    for ( user_id, ( new_password, new_password_repeat ) ) in new_passwords.items():
      if user_id not in allowed_user_ids:
        raise Password_reset_error( "There was an error when resetting your password. Please contact %s." % self.__support_email )

      # skip blank passwords
      if new_password == u"" and new_password_repeat == u"":
        continue

      user = self.__database.load( User, user_id )

      if not user:
        raise Password_reset_error( "There was an error when resetting your password. Please contact %s." % self.__support_email )

      # ensure the passwords match
      if new_password != new_password_repeat:
        raise Password_reset_error( u"The new passwords you entered for user %s do not match. Please try again." % user.username )

      # ensure the new password isn't too long
      if len( new_password ) > 30:
        raise Password_reset_error( u"Your password can be no longer than 30 characters." )

      at_least_one_reset = True
      user.password = new_password
      self.__database.save( user, commit = False )

    # if all the new passwords provided are blank, bail
    if not at_least_one_reset:
      raise Password_reset_error( u"Please enter a new password. Or, if you already know your password, just click the login link above." )

    password_reset.redeemed = True
    self.__database.save( password_reset, commit = False )
    self.__database.commit()

    return dict( redirect = u"/" )

  @expose( view = Json )
  @end_transaction
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    email_addresses = unicode,
    access = Valid_string(),
    invite_button = unicode,
    user_id = Valid_id( none_okay = True ),
  )
  def send_invites( self, notebook_id, email_addresses, access, invite_button, user_id = None ):
    """
    Send notebook invitations to the given email addresses.

    @type notebook_id: unicode
    @param notebook_id: id of the notebook that the invitation is for
    @type email_addresses: unicode
    @param email_addresses: a string containing whitespace- or comma-separated email addresses
    @type access: unicode
    @param access: type of access to grant, either "collaborator", "viewer", or "owner". with
                   certain rate plans, only "viewer" is allowed
    @type invite_button: unicode
    @param invite_button: ignored
    @type user_id: unicode
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: { 'message': message, 'invites': invites }
    @raise Invite_error: an error occured when sending the invite
    @raise Validation_error: one of the arguments is invalid
    @raise Access_error: user_id doesn't have owner-level notebook access to send an invite or
                         doesn't have a rate plan supporting notebook collaboration
    """
    if len( email_addresses ) < 5:
      raise Invite_error( u"Please enter at least one valid email address." )
    if len( email_addresses ) > 5000:
      raise Invite_error( u"Please enter fewer email addresses." )

    if not self.check_access( user_id, notebook_id, read_write = True, owner = True ):
      raise Access_error()

    # except for viewer-only invites, this feature requires a rate plan above basic
    user = self.__database.load( User, user_id )
    plan = self.__rate_plans[ user.rate_plan ]
    if user is None or user.username is None or ( plan[ u"notebook_collaboration" ] != True and access != u"viewer" ):
      raise Access_error()

    if access == u"collaborator":
      read_write = True
      owner = False
    elif access == u"viewer":
      read_write = False
      owner = False
    elif access == u"owner":
      read_write = True
      owner = True
    else:
      raise Access_error()

    notebook = self.__database.load( Notebook, notebook_id )
    if notebook is None:
      raise Access_error()

    # parse email_addresses string into individual email addresses
    email_addresses_list = set()
    for piece in WHITESPACE_OR_COMMA_PATTERN.split( email_addresses ):
      for match in EMBEDDED_EMAIL_ADDRESS_PATTERN.finditer( piece ):
        email_addresses_list.add( match.groups( 0 )[ 0 ] )

    email_count = len( email_addresses_list )

    if email_count == 0:
      raise Invite_error( u"Please enter at least one valid email address." )

    import smtplib
    from email import Message, Charset

    for email_address in email_addresses_list:
      # record the sending of this invite email
      invite_id = self.__database.next_id( Invite, commit = False )
      invite = Invite.create( invite_id, user_id, notebook_id, email_address, read_write, owner )
      self.__database.save( invite, commit = False )

      # update any invitations for this notebook already sent to the same email address
      similar_invites = self.__database.select_many( Invite, invite.sql_load_similar() )
      for similar in similar_invites:
        similar.read_write = read_write
        similar.owner = owner
        self.__database.save( similar, commit = False )

        # if the invite is already redeemed, then update the relevant entry in the user_notebook
        # access table as well
        if similar.redeemed_user_id is not None:
          redeemed_user = self.__database.load( User, similar.redeemed_user_id )
          if redeemed_user:
            self.__database.execute( redeemed_user.sql_update_access( notebook_id, read_write, owner ) )
            notebook = self.__database.load( Notebook, notebook_id )
            if notebook:
              self.__database.execute( redeemed_user.sql_update_access( notebook.trash_id, read_write, owner ) )

      # create an email message with a unique invitation link
      notebook_name = notebook.name.strip().replace( "\n", " " ).replace( "\r", " " )
      message = Message.Message()
      message[ u"From" ] = user.email_address or u"Luminotes personal wiki <%s>" % self.__support_email
      if user.email_address:
        message[ u"Sender" ] = u"Luminotes personal wiki <%s>" % self.__support_email
      message[ u"To" ] = email_address
      message[ u"Subject" ] = notebook_name

      payload = \
        u"I've shared a wiki with you called \"%s\".\n" % notebook_name + \
        u"Please visit the following link to view it online:\n\n" + \
        u"%s/i/%s\n\n" % ( self.__https_url or self.__http_url, invite.object_id )

      # try representing the payload as plain 7-bit ASCII for greatest compatibility
      try:
        str( notebook_name )
        message.set_payload( payload )
      # if that doesn't work, encode the payload as UTF-8 instead
      except UnicodeEncodeError:
        message.set_payload( payload.encode( "utf-8" ) )
        charset = Charset.Charset( "utf-8" )
        charset.body_encoding = Charset.QP
        message.set_charset( charset )

      # send the message out through localhost's smtp server
      server = smtplib.SMTP()
      server.connect()
      server.sendmail( message[ u"From" ], [ email_address ], message.as_string() )
      server.quit()

    self.__database.commit()
    invites = self.__database.select_many( Invite, Invite.sql_load_notebook_invites( notebook_id ) )

    if email_count == 1:
      return dict(
        message = u"An invitation has been sent.",
        invites = invites,
      )
    else:
      return dict(
        message = u"%s invitations have been sent." % email_count,
        invites = invites,
      )

  @expose( view = Json )
  @end_transaction
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    invite_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def revoke_invite( self, notebook_id, invite_id, user_id = None ):
    """
    Revoke the invite's access to the given notebook.

    @type notebook_id: unicode
    @param notebook_id: id of the notebook that the invitation is for
    @type invite_id: unicode
    @param invite_id: id of the invite to revoke
    @type user_id: unicode
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: { 'message': message, 'invites': invites }
    @raise Validation_error: one of the arguments is invalid
    @raise Access_error: user_id doesn't have owner-level notebook access to revoke an invite
    """
    if not self.check_access( user_id, notebook_id, read_write = True, owner = True ):
      raise Access_error()

    invite = self.__database.load( Invite, invite_id )
    notebook = self.__database.load( Notebook, notebook_id )
    if not notebook or not invite or not invite.email_address or invite.notebook_id != notebook_id:
      raise Access_error()

    self.__database.execute(
      User.sql_revoke_invite_access( notebook_id, notebook.trash_id, invite.email_address ),
      commit = False,
    )
    self.__database.execute( invite.sql_revoke_invites(), commit = False )
    self.__database.commit()

    invites = self.__database.select_many( Invite, Invite.sql_load_notebook_invites( notebook_id ) )

    return dict(
      message = u"Notebook access for %s has been revoked." % invite.email_address,
      invites = invites,
    )

  @expose( view = Main_page )
  @end_transaction
  @grab_user_id
  @validate(
    invite_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def redeem_invite( self, invite_id, user_id = None ):
    """
    Begin the process of redeeming a notebook invite.

    @type invite_id: unicode
    @param invite_id: id of invite to redeem
    @type user_id: unicode
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: unicode
    @return: rendered HTML page
    @raise Validation_error: one of the arguments is invalid
    @raise Invite_error: an error occured when redeeming the invite
    """
    invite = self.__database.load( Invite, invite_id )
    if not invite:
      raise Invite_error( "That invite is unknown. Please make sure that you typed the address correctly." )

    if user_id is not None:
      # if the user is logged in but the invite is unredeemed, redeem it and redirect to the notebook
      if invite.redeemed_user_id is None:
        self.convert_invite_to_access( invite, user_id )
        return dict( redirect = u"/notebooks/%s" % invite.notebook_id )

      # if the user is logged in and has already redeemed this invite, then just redirect to the notebook
      if invite.redeemed_user_id == user_id:
        return dict( redirect = u"/notebooks/%s" % invite.notebook_id )
      else:
        raise Invite_error( u"That invite has already been used by someone else." )

    if invite.redeemed_user_id:
      raise Invite_error( u"That invite has already been used. If you were the one who used it, then simply <a href=\"/login\">login</a> to your account." )

    notebook = self.__database.load( Notebook, invite.notebook_id )
    if not notebook:
      raise Invite_error( "That notebook you've been invited to is unknown." )

    anonymous = self.__database.select_one( User, User.sql_load_by_username( u"anonymous" ), use_cache = True )
    if anonymous:
      main_notebook = self.__database.select_one( Notebook, anonymous.sql_load_notebooks( undeleted_only = True ) )
      invite_notebook = self.__database.load( Notebook, invite.notebook_id )

    if not anonymous or not main_notebook or not invite_notebook:
      raise Password_reset_error( "There was an error when redeeming your invite. Please contact %s." % self.__support_email )

    # give the user the option to sign up or login in order to redeem the invite
    result = self.current( anonymous.object_id )
    result[ "notebook" ] = main_notebook
    result[ "startup_notes" ] = self.__database.select_many( Note, main_notebook.sql_load_startup_notes() )
    result[ "total_notes_count" ] = self.__database.select_one( Note, main_notebook.sql_count_notes(), use_cache = True )
    result[ "note_read_write" ] = False
    result[ "notes" ] = [ Note.create(
      object_id = u"redeem_invite",
      contents = unicode( Redeem_invite_note( invite, invite_notebook ) ),
      notebook_id = main_notebook.object_id,
    ) ]
    result[ "invites" ] = []

    return result

  def convert_invite_to_access( self, invite, user_id ):
    """
    Grant the given user access to the notebook specified in the invite, and mark that invite as
    redeemed.

    @type invite: model.Invite
    @param invite: invite to convert to notebook access
    @type user_id: unicode
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @raise Invite_error: an error occured when redeeming the invite
    """
    # prevent a user from redeeming their own invite
    if invite.from_user_id == user_id:
      return

    user = self.__database.load( User, user_id )
    notebook = self.__database.load( Notebook, invite.notebook_id )
    if not user or not notebook:
      raise Invite_error( "There was an error when redeeming your invite. Please contact %s." % self.__support_email )

    # if the user doesn't already have access to this notebook, then grant access
    if not self.__database.select_one( bool, user.sql_has_access( notebook.object_id ) ):
      rank = self.__database.select_one( float, user.sql_highest_notebook_rank() ) + 1
      self.__database.execute( user.sql_save_notebook( notebook.object_id, invite.read_write, invite.owner, rank = rank ), commit = False )

    # the same goes for the trash notebook
    if not self.__database.select_one( bool, user.sql_has_access( notebook.trash_id ) ):
      self.__database.execute( user.sql_save_notebook( notebook.trash_id, invite.read_write, invite.owner ), commit = False )

    invite.redeemed_user_id = user_id
    self.__database.save( invite, commit = False )

    self.__database.commit()

  @expose( view = Blank_page )
  @end_transaction
  def paypal_notify( self, **params ):
    """
    Notify Luminotes of payments, subscriptions, cancellations, refunds, etc.
    This method is responsible for validating the request, POSTing back to
    PayPal to make sure the request is valid, and then updating the user's
    record in the database with their new rate plan. paypal_notify() is
    invoked by PayPal itself.
    """
    #PAYPAL_URL = u"https://www.sandbox.paypal.com/cgi-bin/webscr"
    PAYPAL_URL = u"https://www.paypal.com/cgi-bin/webscr"

    # check that payment_status is Completed
    payment_status = params.get( u"payment_status" )
    if payment_status == u"Refunded":
      return dict() # for now, ignore refunds and let paypal handle them
    if payment_status and payment_status != u"Completed":
      raise Payment_error( u"payment_status is not Completed", params )

    # TODO: check that txn_id is not a duplicate

    # check that receiver_email is mine
    if params.get( u"receiver_email" ) != self.__payment_email:
      raise Payment_error( u"incorrect receiver_email", params )

    # verify mc_currency
    if params.get( u"mc_currency" ) != u"USD":
      raise Payment_error( u"unsupported mc_currency", params )

    # verify item_number
    plan_index = params.get( u"item_number" )
    if plan_index == None:
      return dict() # ignore this transaction if there's no item number

    try:
      plan_index = int( plan_index )
    except ValueError:
      raise Payment_error( u"invalid item_number", params )
    if plan_index == 0 or plan_index >= len( self.__rate_plans ):
      raise Payment_error( u"invalid item_number", params )

    # verify mc_gross
    rate_plan = self.__rate_plans[ plan_index ]
    fee = u"%0.2f" % rate_plan[ u"fee" ]
    yearly_fee = u"%0.2f" % rate_plan[ u"yearly_fee" ]
    mc_gross = params.get( u"mc_gross" )
    if mc_gross and mc_gross not in ( fee, yearly_fee ):
      raise Payment_error( u"invalid mc_gross", params )

    # verify mc_amount3
    mc_amount3 = params.get( u"mc_amount3" )
    if mc_amount3 and mc_amount3 not in ( fee, yearly_fee ):
      raise Payment_error( u"invalid mc_amount3", params )

    # verify item_name
    item_name = params.get( u"item_name" )
    if item_name and item_name.lower() != u"luminotes " + rate_plan[ u"name" ].lower():
      raise Payment_error( u"invalid item_name", params )

    # verify period1 and period2 (should not be present)
    if params.get( u"period1" ) or params.get( u"period2" ):
      raise Payment_error( u"invalid period", params )

    # verify period3
    period3 = params.get( u"period3" )
    if mc_amount3 == yearly_fee:
      if period3 and period3 != u"1 Y": # one-year subscription
        raise Payment_error( u"invalid period3", params )
    else:
      if period3 and period3 != u"1 M": # one-month subscription
        raise Payment_error( u"invalid period3", params )

    params[ u"cmd" ] = u"_notify-validate"
    encoded_params = urllib.urlencode( params )
    
    # ask paypal to verify the request
    request = urllib2.Request( PAYPAL_URL )
    request.add_header( u"Content-type", u"application/x-www-form-urlencoded" )
    request_file = urllib2.urlopen( PAYPAL_URL, encoded_params )
    result = request_file.read()

    if result != u"VERIFIED":
      raise Payment_error( result, params )

    # update the database based on the type of transaction
    txn_type = params.get( u"txn_type" )
    user_id = params.get( u"custom", u"" )
    try:
      user_id = Valid_id()( user_id )
    except ValueError:
      raise Payment_error( u"invalid custom", params )

    user = self.__database.load( User, user_id )
    if not user:
      raise Payment_error( u"unknown custom", params )

    if txn_type in ( u"subscr_signup", u"subscr_modify" ):
      if params.get( u"recurring" ) != u"1":
        raise Payment_error( u"invalid recurring", params )
      user.rate_plan = plan_index
      self.__database.save( user, commit = False )
      self.update_groups( user )
      self.__database.commit()
    elif txn_type == u"subscr_cancel":
      user.rate_plan = 0 # return the user to the free account level
      self.__database.save( user, commit = False )
      self.update_groups( user )
      self.__database.commit()
    elif txn_type in ( u"subscr_payment", u"subscr_failed" ):
      pass # for now, ignore payments and let paypal handle them
    else:
      raise Payment_error( "unknown txn_type", params )

    return dict()

  def update_groups( self, user ):
    """
    Update a user's group membership as a result of a rate plan change. This method does not commit
    the current database transaction.
    """
    rate_plan = self.__rate_plans[ user.rate_plan ]

    # if the user has a rate plan with admin capabilities
    if rate_plan.get( u"user_admin" ) is True:
      has_an_admin_group = False
      groups = self.__database.select_many( Group, user.sql_load_groups() )

      # determine whether the user is the admin of at least one group
      for group in groups:
        if group.admin is False: continue
        has_an_admin_group = True

        # set all users in this group to the same rate plan as the admin
        group_users = self.__database.select_many( User, group.sql_load_users() )
        for group_user in group_users:
          group_user.rate_plan = user.rate_plan
          self.__database.save( group_user )

      # if the user is not an admin of any group, create one for them and make them the admin
      if has_an_admin_group is False:
        group_id = self.__database.next_id( Group, commit = False )
        group = Group.create( group_id, name = u"my group", admin = True )
        self.__database.save( group, commit = False )
        self.__database.execute( user.sql_save_group( group_id, admin = True ), commit = False )

      return

    # otherwise, downgrade the user's group admin access to normal group membership
    groups = self.__database.select_many( Group, user.sql_load_groups() )

    for group in groups:
      if group.admin is False: continue
      self.__database.execute( user.sql_update_group_admin( group.object_id, admin = False ), commit = False )

      # also return all users in this group to the free account level
      group_users = self.__database.select_many( User, group.sql_load_users() )
      for group_user in group_users:
        group_user.rate_plan = 0
        self.__database.save( group_user )

  @expose( view = Main_page )
  @end_transaction
  @grab_user_id
  def thanks( self, **params ):
    """
    Provide the information necessary to display the subscription thanks page.
    """
    anonymous = self.__database.select_one( User, User.sql_load_by_username( u"anonymous" ), use_cache = True )
    if anonymous:
      main_notebook = self.__database.select_one( Notebook, anonymous.sql_load_notebooks( undeleted_only = True ) )
    else:
      main_notebook = None

    result = self.current( params.get( u"user_id" ) )

    rate_plan = params.get( u"item_number", "" )
    try:
      rate_plan = int( rate_plan )
    except ValueError:
      rate_plan = None

    retry_count = params.get( u"retry_count", "" )
    try:
      retry_count = int( retry_count )
    except ValueError:
      retry_count = None

    # if there's no rate plan or we've retried too many times, give up and display an error
    RETRY_TIMEOUT = 15
    if rate_plan is None or retry_count > RETRY_TIMEOUT:
      note = Thanks_error_note()
    # if the rate plan of the subscription matches the user's current rate plan, success
    elif rate_plan == result[ u"user" ].rate_plan:
      note = Thanks_note( self.__rate_plans[ rate_plan ][ u"name" ].capitalize() )
      result[ "conversion" ] = "subscribe_%s" % rate_plan
    # otherwise, display an auto-reloading "processing..." page
    else:
      note = Processing_note( rate_plan, retry_count )

    result[ "notebook" ] = main_notebook
    result[ "startup_notes" ] = self.__database.select_many( Note, main_notebook.sql_load_startup_notes() )
    result[ "total_notes_count" ] = self.__database.select_one( Note, main_notebook.sql_count_notes(), use_cache = True )
    result[ "note_read_write" ] = False
    result[ "notes" ] = [ Note.create(
      object_id = u"thanks",
      contents = unicode( note ),
      notebook_id = main_notebook.object_id,
    ) ]
    result[ "invites" ] = []

    return result

  def rate_plan( self, plan_index ):
    return self.__rate_plans[ plan_index ]

  @expose( view = Json )
  @end_transaction
  @grab_user_id
  @validate(
    email_address = ( Valid_string( min = 0, max = 60 ) ),
    settings_button = unicode,
    user_id = Valid_id( none_okay = True ),
  )
  def update_settings( self, email_address, settings_button, user_id ):
    """
    Update the settings for a particular user.

    @type email_address: unicode
    @param email_address: new email address
    @type settings_button: unicode
    @param settings_button: ignored
    @type user_id: unicode
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: { "email_address": new_email_address }
    @raise Validation_error: one of the arguments is invalid
    @raise Access_error: the given user id is unknown
    """
    if len( email_address ) > 0:
      try:
        email_address = valid_email_address( email_address )
      except ValueError:
        raise Validation_error( "email_address", email_address, valid_email_address )
    else:
      email_address = None

    user = self.__database.load( User, user_id )
    if not user:
      raise Access_error()

    if email_address != user.email_address:
      user.email_address = email_address
      self.__database.save( user )

    return dict(
      email_address = email_address,
    )
