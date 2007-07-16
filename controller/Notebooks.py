import cherrypy
from Scheduler import Scheduler
from Expose import expose
from Validate import validate, Valid_string, Validation_error, Valid_bool
from Database import Valid_id
from Users import grab_user_id
from Updater import wait_for_update, update_client
from Expire import strongly_expire
from Html_nuker import Html_nuker
from Async import async
from model.Notebook import Notebook
from model.Entry import Entry
from view.Main_page import Main_page
from view.Json import Json
from view.Entry_page import Entry_page
from view.Html_file import Html_file


class Access_error( Exception ):
  def __init__( self, message = None ):
    if message is None:
      message = u"You don't have access to that notebook."

    Exception.__init__( self, message )
    self.__message = message

  def to_dict( self ):
    return dict(
      error = self.__message
    )


class Notebooks( object ):
  def __init__( self, scheduler, database ):
    self.__scheduler = scheduler
    self.__database = database

  @expose( view = Main_page )
  @validate(
    notebook_id = Valid_id(),
  )
  def default( self, notebook_id ):
    return dict(
      notebook_id = notebook_id,
    )

  @expose( view = Json )
  @strongly_expire
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def contents( self, notebook_id, user_id ):
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    yield dict(
      notebook = notebook,
    )

  @expose( view = Json )
  @strongly_expire
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    entry_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def load_entry( self, notebook_id, entry_id, user_id ):
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if notebook is None:
      entry = None
    else:
      entry = notebook.lookup_entry( entry_id )

    yield dict(
      entry = entry,
    )

  @expose( view = Json )
  @strongly_expire
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    entry_title = Valid_string( min = 1, max = 500 ),
    user_id = Valid_id( none_okay = True ),
  )
  def load_entry_by_title( self, notebook_id, entry_title, user_id ):
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if notebook is None:
      entry = None
    else:
      entry = notebook.lookup_entry_by_title( entry_title )

    yield dict(
      entry = entry,
    )

  @expose( view = Json )
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    entry_id = Valid_id(),
    contents = Valid_string( min = 1, max = 25000, escape_html = False ),
    startup = Valid_bool(),
    user_id = Valid_id( none_okay = True ),
  )
  def save_entry( self, notebook_id, entry_id, contents, startup, user_id ):
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if not notebook:
      yield dict(
        saved = False,
      )
      return

    self.__database.load( entry_id, self.__scheduler.thread )
    entry = ( yield Scheduler.SLEEP )

    # if the entry is already in the database, load it and update it. otherwise, create it
    if entry and entry in notebook.entries:
      notebook.update_entry( entry, contents )
    else:
      entry = Entry( entry_id, contents )
      notebook.add_entry( entry )

    if startup:
      notebook.add_startup_entry( entry )
    else:
      notebook.remove_startup_entry( entry )

    self.__database.save( notebook )

    yield dict(
      saved = True,
    )

  @expose( view = Json )
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    entry_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def add_startup_entry( self, notebook_id, entry_id, user_id ):
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if not notebook:
      yield dict()
      return # TODO: raising an exception here would be nice

    self.__database.load( entry_id, self.__scheduler.thread )
    entry = ( yield Scheduler.SLEEP )

    if entry:
      notebook.add_startup_entry( entry )
      self.__database.save( notebook )

    yield dict()

  @expose( view = Json )
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    entry_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def remove_startup_entry( self, notebook_id, entry_id, user_id ):
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if not notebook:
      yield dict()
      return # TODO: raising an exception here would be nice

    self.__database.load( entry_id, self.__scheduler.thread )
    entry = ( yield Scheduler.SLEEP )

    if entry:
      notebook.remove_startup_entry( entry )
      self.__database.save( notebook )

    yield dict()

  @expose( view = Json )
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    entry_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def delete_entry( self, notebook_id, entry_id, user_id ):
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if not notebook:
      yield dict()
      return # TODO: raising an exception here would be nice

    self.__database.load( entry_id, self.__scheduler.thread )
    entry = ( yield Scheduler.SLEEP )

    if entry:
      notebook.remove_entry( entry )
      self.__database.save( notebook )

    yield dict()

  @expose( view = Entry_page )
  @validate( id = Valid_id() )
  def blank_entry( self, id ):
    return dict( id = id )

  @expose( view = Json )
  @strongly_expire
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    search_text = Valid_string( min = 0, max = 100 ),
    user_id = Valid_id( none_okay = True ),
  )
  def search( self, notebook_id, search_text, user_id ):
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if not notebook:
      yield dict(
        entries = [],
      )
      return

    search_text = search_text.lower()
    title_matches = []
    content_matches = []
    nuker = Html_nuker()

    if len( search_text ) > 0:
      for entry in notebook.entries:
        if search_text in nuker.nuke( entry.title ).lower():
          title_matches.append( entry )
        elif search_text in nuker.nuke( entry.contents ).lower():
          content_matches.append( entry )

    entries = title_matches + content_matches

    yield dict(
      entries = entries,
    )

  @expose( view = Json )
  @strongly_expire
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def recent_entries( self, notebook_id, user_id ):
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if not notebook:
      yield dict(
        entries = [],
      )
      return

    RECENT_COUNT = 10
    entries = notebook.entries
    entries.sort( lambda a, b: cmp( b.revision, a.revision ) )

    yield dict(
      entries = entries[ :RECENT_COUNT ],
    )

  @expose( view = Html_file )
  @strongly_expire
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def download_html( self, notebook_id, user_id ):
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if not notebook:
      yield dict(
        notebook_name = None,
        entries = [],
      )
      return

    normal_entries = list( set( notebook.entries ) - set( notebook.startup_entries ) )
    normal_entries.sort( lambda a, b: -cmp( a.revision, b.revision ) )
    
    yield dict(
      notebook_name = notebook.name,
      entries = notebook.startup_entries + normal_entries,
    )

  @async
  def check_access( self, notebook_id, user_id, callback ):
    # check if the anonymous user has access to this notebook
    self.__database.load( u"anonymous", self.__scheduler.thread )
    anonymous = ( yield Scheduler.SLEEP )

    access = False
    if anonymous.has_access( notebook_id ):
      access = True

    if user_id:
      # check if the currently logged in user has access to this notebook
      self.__database.load( user_id, self.__scheduler.thread )
      user = ( yield Scheduler.SLEEP )

      if user.has_access( notebook_id ):
        access = True

    yield callback, access

  scheduler = property( lambda self: self.__scheduler )
