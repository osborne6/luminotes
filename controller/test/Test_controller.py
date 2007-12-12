import cherrypy
from Stub_database import Stub_database
from Stub_view import Stub_view
from config import Common
from datetime import datetime
from StringIO import StringIO
from copy import copy


class Test_controller( object ):
  def __init__( self ):
    from model.User import User
    from model.Notebook import Notebook
    from model.Note import Note
    from model.Invite import Invite

    # Since Stub_database isn't a real database and doesn't know SQL, replace some of the
    # SQL-returning methods in User, Note, and Notebook to return functions that manipulate data in
    # Stub_database directly instead. This is all a little fragile, but it's better than relying on
    # the presence of a real database for unit tests.
    def sql_save_notebook( self, notebook_id, read_write, owner, database ):
      if self.object_id in database.user_notebook:
        database.user_notebook[ self.object_id ].append( ( notebook_id, read_write, owner ) )
      else:
        database.user_notebook[ self.object_id ] = [ ( notebook_id, read_write, owner ) ]

    User.sql_save_notebook = lambda self, notebook_id, read_write = False, owner = False: \
      lambda database: sql_save_notebook( self, notebook_id, read_write, owner, database )

    def sql_remove_notebook( self, notebook_id, database ):
      if self.object_id in database.user_notebook:
        for notebook_info in database.user_notebook[ self.object_id ]:
          if notebook_info[ 0 ] == notebook_id:
            database.user_notebook[ self.object_id ].remove( notebook_info )

    User.sql_remove_notebook = lambda self, notebook_id: \
      lambda database: sql_remove_notebook( self, notebook_id, database )

    def sql_load_notebooks( self, parents_only, undeleted_only, database ):
      notebooks = []
      notebook_infos = database.user_notebook.get( self.object_id )

      if not notebook_infos: return []

      for notebook_info in notebook_infos:
        ( notebook_id, read_write, owner ) = notebook_info
        notebook = database.objects.get( notebook_id )[ -1 ]
        notebook.read_write = read_write
        notebook.owner = owner
        if parents_only and notebook.trash_id is None:
          continue
        if undeleted_only and notebook.deleted is True:
          continue
        notebooks.append( notebook )

      return notebooks

    User.sql_load_notebooks = lambda self, parents_only = False, undeleted_only = False: \
      lambda database: sql_load_notebooks( self, parents_only, undeleted_only, database )

    def sql_load_by_username( username, database ):
      users = []

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, User ) and obj.username == username:
          users.append( obj )

      return users

    User.sql_load_by_username = staticmethod( lambda username: \
      lambda database: sql_load_by_username( username, database ) )

    def sql_load_by_email_address( email_address, database ):
      users = []

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, User ) and obj.email_address == email_address:
          users.append( obj )

      return users

    User.sql_load_by_email_address = staticmethod( lambda email_address: \
      lambda database: sql_load_by_email_address( email_address, database ) )

    def sql_calculate_storage( self, database ):
      return ( 17, 3, 4, 22 ) # rather than actually calculating anything, return arbitrary numbers

    User.sql_calculate_storage = lambda self: \
      lambda database: sql_calculate_storage( self, database )

    def sql_has_access( self, notebook_id, read_write, owner, database ):
      for ( user_id, notebook_infos ) in database.user_notebook.items():
        for notebook_info in notebook_infos:
          ( db_notebook_id, db_read_write, db_owner ) = notebook_info

          if self.object_id == user_id and notebook_id == db_notebook_id:
            if read_write is True and db_read_write is False:
              return False
            if owner is True and db_owner is False:
              return False
            return True

      return False

    User.sql_has_access = lambda self, notebook_id, read_write = False, owner = False: \
      lambda database: sql_has_access( self, notebook_id, read_write, owner, database )

    def sql_load_revisions( self, database ):
      note_list = database.objects.get( self.object_id )
      if not note_list: return None

      revisions = [ note.revision for note in note_list ]
      return revisions

    Note.sql_load_revisions = lambda self: \
      lambda database: sql_load_revisions( self, database )

    def sql_load_notes( self, database ):
      notes = []

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, Note ) and obj.notebook_id == self.object_id:
          notes.append( obj )

      notes.sort( lambda a, b: -cmp( a.revision, b.revision ) )
      return notes

    Notebook.sql_load_notes = lambda self: \
      lambda database: sql_load_notes( self, database )

    def sql_load_startup_notes( self, database ):
      notes = []

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, Note ) and obj.notebook_id == self.object_id and obj.startup:
          notes.append( obj )

      return notes

    Notebook.sql_load_startup_notes = lambda self: \
      lambda database: sql_load_startup_notes( self, database )

    def sql_load_recent_notes( self, database, start, count ):
      notes = []

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, Note ) and obj.notebook_id == self.object_id:
          obj = copy( obj )
          obj._Note__creation = database.objects[ object_id ][ 0 ].revision
          notes.append( obj )

      notes.sort( lambda a, b: -cmp( a.creation, b.creation ) )
      notes = notes[ start : start + count ]
      return notes

    Notebook.sql_load_recent_notes = lambda self, start = 0, count = 10: \
      lambda database: sql_load_recent_notes( self, database, start, count )

    def sql_load_note_by_title( self, title, database ):
      notes = []

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, Note ) and obj.notebook_id == self.object_id and obj.title == title:
          notes.append( obj )

      return notes

    Notebook.sql_load_note_by_title = lambda self, title: \
      lambda database: sql_load_note_by_title( self, title, database )

    def sql_search_notes( self, search_text, database ):
      notes = []
      search_text = search_text.lower()

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, Note ) and obj.notebook_id == self.object_id and \
           search_text in obj.contents.lower():
          notes.append( obj )

      return notes

    Notebook.sql_search_notes = lambda self, search_text: \
      lambda database: sql_search_notes( self, search_text, database )

    def sql_highest_rank( self, database ):
      max_rank = -1

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, Note ) and obj.notebook_id == self.object_id and obj.rank > max_rank:
          max_rank = obj.rank

      return max_rank

    Notebook.sql_highest_rank = lambda self: \
      lambda database: sql_highest_rank( self, database )

    def sql_count_notes( self, database ):
      count = 0

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, Note ) and obj.notebook_id == self.object_id:
          count += 1

      return count

    Notebook.sql_count_notes = lambda self: \
      lambda database: sql_count_notes( self, database )

    def sql_load_similar( self, database ):
      invites = []

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, Invite ) and obj.from_user_id == self.from_user_id and \
           obj.notebook_id == self.notebook_id and obj.email_address == self.email_address and \
           obj.redeemed_user_id is None and obj.object_id != self.object_id:
          invites.append( obj )

      return invites

    Invite.sql_load_similar = lambda self: \
      lambda database: sql_load_similar( self, database )

    def sql_load_notebook_invites( notebook_id, database ):
      invites = []

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, Invite ) and obj.notebook_id == notebook_id and \
           obj.email_address not in [ i.email_address for i in invites ]:
          invites.append( obj )

      return invites

    Invite.sql_load_notebook_invites = staticmethod( lambda notebook_id:
      lambda database: sql_load_notebook_invites( notebook_id, database ) )

  def setUp( self ):
    from controller.Root import Root
    cherrypy.lowercase_api = True
    self.database = Stub_database()
    self.settings = {
      u"global": {
        u"luminotes.http_url" : u"http://luminotes.com",
        u"luminotes.https_url" : u"https://luminotes.com",
        u"luminotes.http_proxy_ip" : u"127.0.0.1",
        u"luminotes.https_proxy_ip" : u"127.0.0.2",
        u"luminotes.support_email": "unittest@luminotes.com",
        u"luminotes.rate_plans": [
          {
            u"name": u"super",
            u"storage_quota_bytes": 1337,
          },
          {
            u"name": "extra super",
            u"storage_quota_bytes": 31337,
          },
        ],
      },
    }

    cherrypy.root = Root( self.database, self.settings )
    cherrypy.config.update( Common.settings )
    cherrypy.config.update( { u"server.log_to_screen": False } )
    cherrypy.server.start( init_only = True, server_class = None )

    # since we only want to test the controller, use the stub view for all exposed methods
    import controller.Expose
    Stub_view.result = None
    controller.Expose.view_override = Stub_view

  def tearDown( self ):
    cherrypy.server.stop()

  def http_get( self, http_path, headers = None, session_id = None, pretend_https = False ):
    """
    Perform an HTTP GET with the given path on the test server. Return the result dict as returned
    by the invoked method.
    """
    if headers is None:
      headers = []

    if session_id:
      headers.append( ( u"Cookie", "session_id=%s" % session_id ) ) # will break if unicode is used for the value

    if pretend_https:
      proxy_ip = self.settings[ "global" ].get( u"luminotes.https_proxy_ip" )
    else:
      proxy_ip = self.settings[ "global" ].get( u"luminotes.http_proxy_ip" )

    request = cherrypy.server.request( ( proxy_ip, 1234 ), u"127.0.0.5" )
    response = request.run( "GET %s HTTP/1.0" % str( http_path ), headers = headers, rfile = StringIO() )
    session_id = response.simple_cookie.get( u"session_id" )
    if session_id: session_id = session_id.value

    try:
      if Stub_view.result is not None:
        result = Stub_view.result
      else:
        result = dict(
          status = response.status,
          headers = response.headers,
          body = response.body,
        )

      result[ u"session_id" ] = session_id
      return result
    finally:
      request.close()

  def http_post( self, http_path, form_args, headers = None, session_id = None ):
    """
    Perform an HTTP POST with the given path on the test server, sending the provided form_args
    dict. Return the result dict as returned by the invoked method.
    """
    from urllib import urlencode
    post_data = urlencode( form_args )

    if headers is None:
      headers = []

    headers.extend( [
      ( u"Content-Type", u"application/x-www-form-urlencoded" ),
      ( u"Content-Length", unicode( len( post_data ) ) ),
    ] )

    if session_id:
      headers.append( ( u"Cookie", "session_id=%s" % session_id ) ) # will break if unicode is used for the value

    request = cherrypy.server.request( ( u"127.0.0.1", 1234 ), u"127.0.0.5" )
    response = request.run( "POST %s HTTP/1.0" % str( http_path ), headers = headers, rfile = StringIO( post_data ) )
    session_id = response.simple_cookie.get( u"session_id" )
    if session_id: session_id = session_id.value

    try:
      if Stub_view.result is not None:
        result = Stub_view.result
      else:
        result = dict(
          status = response.status,
          headers = response.headers,
          body = response.body,
        )

      result[ u"session_id" ] = session_id
      return result
    finally:
      request.close()
