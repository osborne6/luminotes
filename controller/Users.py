import re
import cherrypy
from model.User import User
from model.Notebook import Notebook
from model.Entry import Entry
from Scheduler import Scheduler
from Expose import expose
from Validate import validate, Valid_string, Validation_error
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
  def __init__( self, scheduler, database ):
    self.__scheduler = scheduler
    self.__database = database

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
    if password != password_repeat:
      raise Signup_error( u"The passwords you entered do not match. Please try again." )

    self.__database.load( username, self.__scheduler.thread )
    user = ( yield Scheduler.SLEEP )

    if user is not None:
      raise Signup_error( u"Sorry, that username is not available. Please try something else." )

    # create a notebook for this user
    self.__database.next_id( self.__scheduler.thread )
    notebook_id = ( yield Scheduler.SLEEP )
    notebook = Notebook( notebook_id, u"my notebook" )

    # create a startup entry for this user's notebook
    self.__database.next_id( self.__scheduler.thread )
    entry_id = ( yield Scheduler.SLEEP )
    entry = Entry( entry_id, file( u"static/html/welcome to your wiki.html" ).read() )
    notebook.add_entry( entry )
    notebook.add_startup_entry( entry )

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
    self.__database.load( username, self.__scheduler.thread )
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
    yield dict(
      redirect = u"/",
      deauthenticated = True,
    )

  @expose( view = Json )
  @strongly_expire
  @grab_user_id
  @wait_for_update
  @async
  @update_client
  @validate(
    user_id = Valid_id( none_okay = True ),
  )
  def current( self, user_id ):
    # if there's no logged-in user, default to the anonymous user
    self.__database.load( user_id or u"anonymous", self.__scheduler.thread )
    user = ( yield Scheduler.SLEEP )

    if not user:
      yield dict(
        user = None,
        notebooks = None,
      )
      return

    # in addition to this user's own notebooks, add to that list the anonymous user's notebooks
    if user_id:
      self.__database.load( u"anonymous", self.__scheduler.thread )
      anonymous = ( yield Scheduler.SLEEP )
      notebooks = anonymous.notebooks
    else:
      notebooks = []
    notebooks += user.notebooks

    yield dict(
      user = user,
      notebooks = notebooks,
    )

  scheduler = property( lambda self: self.__scheduler )
