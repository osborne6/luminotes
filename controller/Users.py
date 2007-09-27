import re
import cherrypy
from datetime import datetime, timedelta
from model.User import User
from model.Notebook import Notebook
from model.Note import Note
from model.Password_reset import Password_reset
from Scheduler import Scheduler
from Expose import expose
from Validate import validate, Valid_string, Valid_bool, Validation_error
from Database import Valid_id
from Updater import update_client, wait_for_update
from Expire import strongly_expire
from Async import async
from view.Json import Json
from view.Main_page import Main_page
from view.Redeem_reset_note import Redeem_reset_note


USERNAME_PATTERN = re.compile( "^[a-zA-Z0-9]+$" )
EMAIL_ADDRESS_PATTERN = re.compile( "^[\w.+]+@\w+(\.\w+)+$" )


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
      cherrypy.session[ u"user_id" ] = user.object_id
      cherrypy.session[ u"username" ] = user.username

    if result.get( "deauthenticated" ):
      cherrypy.session.pop( u"user_id", None )
      cherrypy.session.pop( u"username", None )

    return result

  return handle_result


class Users( object ):
  """
  Controller for dealing with users, corresponding to the "/users" URL.
  """
  def __init__( self, scheduler, database, http_url, https_url, support_email, rate_plans ):
    """
    Create a new Users object.

    @type scheduler: controller.Scheduler
    @param scheduler: scheduler to use for asynchronous calls
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
    self.__scheduler = scheduler
    self.__database = database
    self.__http_url = http_url
    self.__https_url = https_url
    self.__support_email = support_email
    self.__rate_plans = rate_plans

  @expose( view = Json )
  @update_auth
  @wait_for_update
  @async
  @update_client
  @validate(
    username = ( Valid_string( min = 1, max = 30 ), valid_username ),
    password = Valid_string( min = 1, max = 30 ),
    password_repeat = Valid_string( min = 1, max = 30 ),
    email_address = ( Valid_string( min = 1, max = 60 ), valid_email_address ),
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

    self.__database.load( "User %s" % username, self.__scheduler.thread )
    user = ( yield Scheduler.SLEEP )

    if user is not None:
      raise Signup_error( u"Sorry, that username is not available. Please try something else." )

    # create a notebook for this user, along with a trash for that notebook
    self.__database.next_id( self.__scheduler.thread )
    trash_id = ( yield Scheduler.SLEEP )
    trash = Notebook( trash_id, u"trash" )

    self.__database.next_id( self.__scheduler.thread )
    notebook_id = ( yield Scheduler.SLEEP )
    notebook = Notebook( notebook_id, u"my notebook", trash )

    # create a startup note for this user's notebook
    self.__database.next_id( self.__scheduler.thread )
    note_id = ( yield Scheduler.SLEEP )
    note = Note( note_id, file( u"static/html/welcome to your wiki.html" ).read() )
    notebook.add_note( note )
    notebook.add_startup_note( note )

    # actually create the new user
    self.__database.next_id( self.__scheduler.thread )
    user_id = ( yield Scheduler.SLEEP )

    user = User( user_id, username, password, email_address, notebooks = [ notebook ] )
    self.__database.save( user )

    # add the new user to the user list
    self.__database.load( u"User_list all", self.scheduler.thread )
    user_list = ( yield Scheduler.SLEEP )
    if user_list:
      user_list.add_user( user )
      self.__database.save( user_list )

    redirect = u"/notebooks/%s" % notebook.object_id

    yield dict(
      redirect = redirect,
      authenticated = user,
    )

  @expose( view = Json )
  @update_auth
  @wait_for_update
  @async
  @update_client
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
    self.__database.load( "User %s" % username, self.__scheduler.thread )
    user = ( yield Scheduler.SLEEP )

    if user is None or user.check_password( password ) is False:
      raise Authentication_error( u"Invalid username or password." )

    # redirect to the user's first notebook (if any)
    if len( user.notebooks ) > 0:
      redirect = u"/notebooks/%s" % user.notebooks[ 0 ].object_id
    else:
      redirect = u"/"

    yield dict(
      redirect = redirect,
      authenticated = user,
    )

  @expose( view = Json )
  @update_auth
  @wait_for_update
  @async
  @update_client
  def logout( self ):
    """
    Deauthenticate the user and log them out of their current session.

    @rtype: json dict
    @return: { 'redirect': url, 'deauthenticated': True }
    """
    yield dict(
      redirect = self.__http_url + u"/",
      deauthenticated = True,
    )

  @expose( view = Json )
  @strongly_expire
  @grab_user_id
  @wait_for_update
  @async
  @update_client
  @validate(
    include_startup_notes = Valid_bool(),
    user_id = Valid_id( none_okay = True ),
  )
  def current( self, include_startup_notes, user_id ):
    """
    Return information on the currently logged-in user. If not logged in, default to the anonymous
    user.

    @type include_startup_notes: bool
    @param include_startup_notes: True to return startup notes for the first notebook
    @type user_id: unicode
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: {
      'user': userdict or None,
      'notebooks': notebooksdict,
      'startup_notes': noteslist,
      'http_url': url,
      'login_url': url,
      'rate_plan': rateplandict,
    }
    @raise Validation_error: one of the arguments is invalid
    """
    # if there's no logged-in user, default to the anonymous user
    self.__database.load( user_id or u"User anonymous", self.__scheduler.thread )
    user = ( yield Scheduler.SLEEP )

    if not user:
      yield dict(
        user = None,
        notebooks = None,
        http_url = u"",
      )
      return

    # in addition to this user's own notebooks, add to that list the anonymous user's notebooks
    self.__database.load( u"User anonymous", self.__scheduler.thread )
    anonymous = ( yield Scheduler.SLEEP )
    login_url = None

    if user_id:
      notebooks = anonymous.notebooks
    else:
      notebooks = []
      if len( anonymous.notebooks ) > 0:
        anon_notebook = anonymous.notebooks[ 0 ]
        login_note = anon_notebook.lookup_note_by_title( u"login" )
        if login_note:
          login_url = "%s/notebooks/%s?note_id=%s" % ( self.__https_url, anon_notebook.object_id, login_note.object_id )

    notebooks += user.notebooks

    yield dict(
      user = user,
      notebooks = notebooks,
      startup_notes = include_startup_notes and len( notebooks ) > 0 and notebooks[ 0 ].startup_notes or [],
      http_url = self.__http_url,
      login_url = login_url,
      rate_plan = ( user.rate_plan < len( self.__rate_plans ) ) and self.__rate_plans[ user.rate_plan ] or {},
    )

  def calculate_storage( self, user ):
    """
    Calculate total storage utilization for all notebooks and all notes of the given user,
    including storage for all past revisions.
    @type user: User
    @param user: user for which to calculate storage utilization
    @rtype: int
    @return: total bytes used for storage
    """
    total_bytes = 0

    def sum_revisions( obj ):
      return \
        self.__database.size( obj.object_id ) + \
        sum( [ self.__database.size( obj.object_id, revision ) or 0 for revision in obj.revisions_list ], 0 )

    def sum_notebook( notebook ):
      return \
        self.__database.size( notebook.object_id ) + \
        sum( [ sum_revisions( note ) for note in notebook.notes ], 0 )

    for notebook in user.notebooks:
      total_bytes += sum_notebook( notebook )

      if notebook.trash:
        total_bytes += sum_notebook( notebook.trash )

    return total_bytes

  @async
  def update_storage( self, user_id, callback = None ):
    """
    Calculate and record total storage utilization for the given user.
    @type user_id: unicode or NoneType
    @param user_id: id of user for which to calculate storage utilization
    @type callback: generator or NoneType
    @param callback: generator to wakeup when the update is complete (optional)
    """
    self.__database.load( user_id, self.__scheduler.thread )
    user = ( yield Scheduler.SLEEP )

    if user:
      user.storage_bytes = self.calculate_storage( user )

    yield callback, user

  @expose( view = Json )
  @wait_for_update
  @async
  @update_client
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
    @return: { 'error': message }
    @raise Password_reset_error: an error occured when sending the password reset email
    @raise Validation_error: one of the arguments is invalid
    """
    import sha
    import random
    import smtplib
    from email import Message

    # check whether there are actually any users with the given email address
    self.__database.load( u"User_list all", self.scheduler.thread )
    user_list = ( yield Scheduler.SLEEP )

    if not user_list:
      raise Password_reset_error( "There was an error when sending your password reset email. Please contact %s." % self.__support_email )

    users = [ user for user in user_list.users if user.email_address == email_address ]
    if len( users ) == 0:
      raise Password_reset_error( u"There are no Luminotes users with the email address %s" % email_address )

    # record the sending of this reset email
    self.__database.next_id( self.__scheduler.thread )
    password_reset_id = ( yield Scheduler.SLEEP )
    password_reset = Password_reset( password_reset_id, email_address )
    self.__database.save( password_reset )

    # create an email message with a unique link
    message = Message.Message()
    message[ u"from" ] = u"Luminotes support <%s>" % self.__support_email
    message[ u"to" ] = email_address
    message[ u"subject" ] = u"Luminotes password reset"
    message.set_payload(
      u"Someone has requested a password reset for a Luminotes user with your email\n" +
      u"address. If this someone is you, please visit the following link for a\n" +
      u"username reminder or a password reset:\n\n" +
      u"%s/%s\n\n" % ( self.__https_url or self.__http_url, password_reset.object_id ) +
      u"This link will expire in 24 hours.\n\n" +
      u"Thanks!"
    )

    # send the message out through localhost's smtp server
    server = smtplib.SMTP()
    server.connect()
    server.sendmail( message[ u"from" ], [ email_address ], message.as_string() )
    server.quit()

    yield dict(
      message = u"Please check your inbox. A password reset email has been sent to %s" % email_address,
    )

  @expose( view = Main_page )
  @strongly_expire
  @wait_for_update
  @async
  @update_client
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
    self.__database.load( u"User anonymous", self.__scheduler.thread )
    anonymous = ( yield Scheduler.SLEEP )

    if not anonymous or len( anonymous.notebooks ) == 0:
      raise Password_reset_error( "There was an error when completing your password reset. Please contact %s." % self.__support_email )

    self.__database.load( password_reset_id, self.__scheduler.thread )
    password_reset = ( yield Scheduler.SLEEP )

    if not password_reset or datetime.now() - password_reset.revision > timedelta( hours = 25 ):
      raise Password_reset_error( "Your password reset link has expired. Please request a new password reset email." )

    if password_reset.redeemed:
      raise Password_reset_error( "Your password has already been reset. Please request a new password reset email." )

    self.__database.load( u"User_list all", self.__scheduler.thread )
    user_list = ( yield Scheduler.SLEEP )

    if not user_list:
      raise Password_reset_error( u"There are no Luminotes users with the email address %s" % password_reset.email_address )

    # find the user(s) with the email address from the password reset request
    matching_users = [ user for user in user_list.users if user.email_address == password_reset.email_address ]

    if len( matching_users ) == 0:
      raise Password_reset_error( u"There are no Luminotes users with the email address %s" % password_reset.email_address )

    yield dict(
      notebook_id = anonymous.notebooks[ 0 ].object_id,
      note_id = u"blank",
      note_contents = unicode( Redeem_reset_note( password_reset_id, matching_users ) ),
    )

  @expose( view = Json )
  @wait_for_update
  @async
  @update_client
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

    self.__database.load( password_reset_id, self.__scheduler.thread )
    password_reset = ( yield Scheduler.SLEEP )

    if not password_reset or datetime.now() - password_reset.revision > timedelta( hours = 25 ):
      raise Password_reset_error( "Your password reset link has expired. Please request a new password reset email." )

    if password_reset.redeemed:
      raise Password_reset_error( "Your password has already been reset. Please request a new password reset email." )

    self.__database.load( u"User_list all", self.__scheduler.thread )
    user_list = ( yield Scheduler.SLEEP )

    if not user_list:
        raise Password_reset_error( "There was an error when resetting your password. Please contact %s." % self.__support_email )

    # find the user(s) with the email address from the password reset request
    matching_users = [ user for user in user_list.users if user.email_address == password_reset.email_address ]
    allowed_user_ids = [ user.object_id for user in matching_users ]

    # reset any passwords that are non-blank
    users_to_reset = []
    for ( user_id, ( new_password, new_password_repeat ) ) in new_passwords.items():
      if user_id not in allowed_user_ids:
        raise Password_reset_error( "There was an error when resetting your password. Please contact %s." % self.__support_email )

      # skip blank passwords
      if new_password == u"" and new_password_repeat == u"":
        continue

      self.__database.load( user_id, self.__scheduler.thread )
      user = ( yield Scheduler.SLEEP )

      if not user:
        raise Password_reset_error( "There was an error when resetting your password. Please contact %s." % self.__support_email )

      # ensure the passwords match
      if new_password != new_password_repeat:
        raise Password_reset_error( u"The new passwords you entered for user %s do not match. Please try again." % user.username )

      # ensure the new password isn't too long
      if len( new_password ) > 30:
        raise Password_reset_error( u"Your password can be no longer than 30 characters." )

      users_to_reset.append( ( user, new_password ) )

    for ( user, new_password ) in users_to_reset:
      user.password = new_password
      self.__database.save( user )

    # if all the new passwords provided are blank, bail
    if not users_to_reset:
      raise Password_reset_error( u"Please enter a new password. Or, if you already know your password, just click the login link above." )

    password_reset.redeemed = True
    self.__database.save( password_reset )

    yield dict( redirect = u"/" )

  scheduler = property( lambda self: self.__scheduler )
