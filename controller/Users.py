import re
import cherrypy
from model.User import User
from model.Notebook import Notebook
from model.Note import Note
from Scheduler import Scheduler
from Expose import expose
from Validate import validate, Valid_string, Valid_bool, Validation_error
from Database import Valid_id
from Updater import update_client, wait_for_update
from Expire import strongly_expire
from Async import async
from view.Json import Json


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
  def __init__( self, scheduler, database, http_url, https_url ):
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
    @rtype: Users
    @return: newly constructed Users
    """
    self.__scheduler = scheduler
    self.__database = database
    self.__http_url = http_url
    self.__https_url = https_url

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
    @return: { 'user': userdict or None, 'notebooks': notebooksdict, 'http_url': url }
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
    )

  scheduler = property( lambda self: self.__scheduler )
