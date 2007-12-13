import re
import cherrypy
from pytz import utc
from datetime import datetime, timedelta
from model.User import User
from model.Notebook import Notebook
from model.Note import Note
from model.Password_reset import Password_reset
from model.Invite import Invite
from Expose import expose
from Validate import validate, Valid_string, Valid_bool, Validation_error
from Database import Valid_id
from Expire import strongly_expire
from view.Json import Json
from view.Main_page import Main_page
from view.Redeem_reset_note import Redeem_reset_note


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
      args[ arg_index ] = cherrypy.session.get( "user_id" )
    else:
      kwargs[ "user_id" ] = cherrypy.session.get( "user_id" )

    return function( *args, **kwargs )
  
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
  def __init__( self, database, http_url, https_url, support_email, rate_plans ):
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
    @type rate_plans: [ { "name": unicode, "storage_quota_bytes": int } ]
    @param rate_plans: list of configured rate plans
    @rtype: Users
    @return: newly constructed Users
    """
    self.__database = database
    self.__http_url = http_url
    self.__https_url = https_url
    self.__support_email = support_email
    self.__rate_plans = rate_plans

  @expose( view = Json )
  @update_auth
  @validate(
    username = ( Valid_string( min = 1, max = 30 ), valid_username ),
    password = Valid_string( min = 1, max = 30 ),
    password_repeat = Valid_string( min = 1, max = 30 ),
    email_address = ( Valid_string( min = 0, max = 60 ) ),
    signup_button = unicode,
  )
  def signup( self, username, password, password_repeat, email_address, signup_button ):
    """
    Create a new User based on the given information. Start that user with their own Notebook and a
    "welcome to your wiki" Note. For convenience, login the newly created user as well.

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
    @rtype: json dict
    @return: { 'redirect': url, 'authenticated': userdict }
    @raise Signup_error: passwords don't match or the username is unavailable
    @raise Validation_error: one of the arguments is invalid
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
    user = User.create( user_id, username, password, email_address )
    self.__database.save( user, commit = False )

    # record the fact that the new user has access to their new notebook
    self.__database.execute( user.sql_save_notebook( notebook_id, read_write = True, owner = True ), commit = False )
    self.__database.execute( user.sql_save_notebook( trash_id, read_write = True, owner = True ), commit = False )
    self.__database.commit()

    redirect = u"/notebooks/%s" % notebook.object_id

    return dict(
      redirect = redirect,
      authenticated = user,
    )

  @expose()
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
    self.__database.execute( user.sql_save_notebook( notebook_id, read_write = True, owner = True ), commit = False )
    self.__database.execute( user.sql_save_notebook( trash_id, read_write = True, owner = True ), commit = False )
    self.__database.commit()

    redirect = u"/notebooks/%s" % notebook.object_id

    return dict(
      redirect = redirect,
      authenticated = user,
    )

  @expose( view = Json )
  @update_auth
  @validate(
    username = ( Valid_string( min = 1, max = 30 ), valid_username ),
    password = Valid_string( min = 1, max = 30 ),
    login_button = unicode,
  )
  def login( self, username, password, login_button ):
    """
    Attempt to authenticate the user. If successful, associate the given user with the current
    session.

    @type username: unicode (alphanumeric only)
    @param username: username to login
    @type password: unicode
    @param password: the user's password
    @rtype: json dict
    @return: { 'redirect': url, 'authenticated': userdict }
    @raise Authentication_error: invalid username or password
    @raise Validation_error: one of the arguments is invalid
    """
    user = self.__database.select_one( User, User.sql_load_by_username( username ) )

    if user is None or user.check_password( password ) is False:
      raise Authentication_error( u"Invalid username or password." )

    first_notebook = self.__database.select_one( Notebook, user.sql_load_notebooks( parents_only = True, undeleted_only = True ) )

    # redirect to the user's first notebook (if any)
    if first_notebook:
      redirect = u"/notebooks/%s" % first_notebook.object_id
    else:
      redirect = u"/"

    return dict(
      redirect = redirect,
      authenticated = user,
    )

  @expose( view = Json )
  @update_auth
  def logout( self ):
    """
    Deauthenticate the user and log them out of their current session.

    @rtype: json dict
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
    }
    @raise Validation_error: one of the arguments is invalid
    @raise Access_error: user_id or anonymous user unknown
    """
    # if there's no logged-in user, default to the anonymous user
    anonymous = self.__database.select_one( User, User.sql_load_by_username( u"anonymous" ) )
    if user_id:
      user = self.__database.load( User, user_id )
    else:
      user = anonymous

    if not user or not anonymous:
      raise Access_error()

    # in addition to this user's own notebooks, add to that list the anonymous user's notebooks
    login_url = None
    anon_notebooks = self.__database.select_many( Notebook, anonymous.sql_load_notebooks( undeleted_only = True ) )

    if user_id and user_id != anonymous.object_id:
      notebooks = self.__database.select_many( Notebook, user.sql_load_notebooks() )
    # if the user is not logged in, return a login URL
    else:
      notebooks = []
      if len( anon_notebooks ) > 0 and anon_notebooks[ 0 ]:
        main_notebook = anon_notebooks[ 0 ]
        login_note = self.__database.select_one( Note, main_notebook.sql_load_note_by_title( u"login" ) )
        if login_note:
          login_url = "%s/notebooks/%s?note_id=%s" % ( self.__https_url, main_notebook.object_id, login_note.object_id )

    return dict(
      user = user,
      notebooks = notebooks + anon_notebooks,
      login_url = login_url,
      logout_url = self.__https_url + u"/",
      rate_plan = ( user.rate_plan < len( self.__rate_plans ) ) and self.__rate_plans[ user.rate_plan ] or {},
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
    anonymous = self.__database.select_one( User, User.sql_load_by_username( u"anonymous" ) )

    if self.__database.select_one( bool, anonymous.sql_has_access( notebook_id, read_write, owner ) ):
      return True

    if user_id:
      # check if the given user has access to this notebook
      user = self.__database.load( User, user_id )

      if user and self.__database.select_one( bool, user.sql_has_access( notebook_id, read_write, owner ) ):
        return True

    return False

  @expose( view = Json )
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
    anonymous = self.__database.select_one( User, User.sql_load_by_username( u"anonymous" ) )
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
    result[ "total_notes_count" ] = self.__database.select_one( Note, main_notebook.sql_count_notes() )
    result[ "note_read_write" ] = False
    result[ "notes" ] = [ Note.create(
      object_id = u"password_reset",
      contents = unicode( Redeem_reset_note( password_reset_id, matching_users ) ),
      notebook_id = main_notebook.object_id,
    ) ]
    result[ "invites" ] = []

    return result

  @expose( view = Json )
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
    @raise Password_reset_error: an error occured when sending the password reset email
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

    # this feature requires a rate plan above basic
    user = self.__database.load( User, user_id )
    if user is None or user.username is None or ( user.rate_plan == 0 and access != u"viewer" ):
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
    from email import Message

    for email_address in email_addresses_list:
      # record the sending of this invite email
      invite_id = self.__database.next_id( Invite, commit = False )
      invite = Invite.create( invite_id, user_id, notebook_id, email_address, read_write, owner )
      self.__database.save( invite, commit = False )

      # update any unredeemed invitations for this notebook already sent to the same email address
      similar_invites = self.__database.select_many( Invite, invite.sql_load_similar() )
      for similar in similar_invites:
        similar.read_write = read_write
        similar.owner = owner
        self.__database.save( similar, commit = False )

      # create an email message with a unique invitation link
      notebook_name = notebook.name.strip().replace( "\n", " " ).replace( "\r", " " )
      message = Message.Message()
      message[ u"From" ] = user.email_address or u"Luminotes personal wiki <%s>" % self.__support_email
      if user.email_address:
        message[ u"Sender" ] = u"Luminotes personal wiki <%s>" % self.__support_email
      message[ u"To" ] = email_address
      message[ u"Subject" ] = notebook_name
      message.set_payload(
        u"I've shared a wiki with you called \"%s\".\n" % notebook_name +
        u"Please visit the following link to view it online:\n\n" +
        u"%s/i/%s\n\n" % ( self.__https_url or self.__http_url, invite.object_id )
      )

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
