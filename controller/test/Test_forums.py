import urllib
import cherrypy
from datetime import datetime
from model.Note import Note
from model.Notebook import Notebook
from model.User import User
from model.Tag import Tag
from Test_controller import Test_controller


class Test_forums( Test_controller ):
  def setUp( self ):
    Test_controller.setUp( self )

    self.notebook = Notebook.create( self.database.next_id( Notebook ), u"my notebook", trash_id = u"foo" )
    self.database.save( self.notebook )

    self.anon_notebook = Notebook.create( self.database.next_id( Notebook ), u"Luminotes" )
    self.database.save( self.anon_notebook )
    self.anon_note = Note.create(
      self.database.next_id( Note ), u"<h3>my note</h3>",
      notebook_id = self.anon_notebook.object_id,
    )
    self.database.save( self.anon_note )

    self.login_note = Note.create(
      self.database.next_id( Note ), u"<h3>login</h3>",
      notebook_id = self.anon_notebook.object_id,
    )
    self.database.save( self.login_note )

    self.username = u"mulder"
    self.password = u"trustno1"
    self.email_address = u"outthere@example.com"
    self.user = None
    self.session_id = None

    self.user = User.create( self.database.next_id( User ), self.username, self.password, self.email_address )
    self.database.save( self.user )
    self.database.execute( self.user.sql_save_notebook( self.notebook.object_id ) )

    self.anonymous = User.create( self.database.next_id( User ), u"anonymous" )
    self.database.save( self.anonymous )
    self.database.execute( self.anonymous.sql_save_notebook( self.anon_notebook.object_id ) )

    tag_id = self.database.next_id( Tag )
    self.forum_tag = Tag.create(
      tag_id,
      notebook_id = None, # this tag is not in the namespace of a single notebook
      user_id = self.anonymous.object_id,
      name = u"forum",
      description = u"a discussion forum"
    )
    self.database.save( self.forum_tag )

    self.general_thread = Notebook.create( self.database.next_id( Notebook ), u"Welcome to the general forum!" )
    self.database.save( self.general_thread )
    self.database.execute(
      self.anonymous.sql_save_notebook( self.general_thread.object_id, read_write = Notebook.READ_WRITE_FOR_OWN_NOTES ),
    )
    self.database.execute(
      self.anonymous.sql_save_notebook_tag( self.general_thread.object_id, self.forum_tag.object_id, value = u"general" ),
    )

    self.support_thread = Notebook.create( self.database.next_id( Notebook ), u"Welcome to the support forum!" )
    self.database.save( self.support_thread )
    self.database.execute(
      self.anonymous.sql_save_notebook( self.support_thread.object_id, read_write = Notebook.READ_WRITE_FOR_OWN_NOTES ),
    )
    self.database.execute(
      self.anonymous.sql_save_notebook_tag( self.support_thread.object_id, self.forum_tag.object_id, value = u"support" ),
    )

  def test_index( self ):
    result = self.http_get( "/forums/" )

    assert result
    assert result.get( u"redirect" ) is None
    assert result[ u"user" ].username == u"anonymous"
    assert len( result[ u"notebooks" ] ) == 3
    assert result[ u"first_notebook" ] == None
    assert result[ u"login_url" ] == u"https://luminotes.com/notebooks/%s?note_id=%s" % (
      self.anon_notebook.object_id, self.login_note.object_id,
    )
    assert result[ u"logout_url" ] == u"https://luminotes.com/users/logout"
    assert result[ u"rate_plan" ]

  def test_index_with_login( self ):
    self.login()

    result = self.http_get( "/forums/", session_id = self.session_id )

    assert result
    assert result.get( u"redirect" ) is None
    assert result[ u"user" ].username == self.user.username
    assert len( result[ u"notebooks" ] ) == 4
    assert result[ u"first_notebook" ].object_id == self.notebook.object_id
    assert result[ u"login_url" ] == None
    assert result[ u"logout_url" ] == u"https://luminotes.com/users/logout"
    assert result[ u"rate_plan" ]

  @staticmethod
  def __assert_threads_equal( thread1, thread2 ):
    assert thread1.object_id == thread2.object_id
    assert thread1.revision == thread2.revision
    assert thread1.name == thread2.name
    assert thread1.trash_id == thread2.trash_id
    assert thread1.read_write == thread2.read_write
    assert thread1.owner == thread2.owner
    assert thread1.deleted == thread2.deleted
    assert thread1.user_id == thread2.user_id
    assert thread1.rank == thread2.rank

  def test_general( self ):
    result = self.http_get( "/forums/general/" )

    assert result[ u"forum_name" ] == u"general"
    assert len( result[ u"threads" ] ) == 1

    self.__assert_threads_equal( result[ u"threads" ][ 0 ], self.general_thread )

    assert result[ u"start" ] == 0
    assert result[ u"count" ] == 50
    assert result[ u"total_thread_count" ] == 1

  def test_support( self ):
    result = self.http_get( "/forums/support/" )

    assert result[ u"forum_name" ] == u"support"
    assert len( result[ u"threads" ] ) == 1

    self.__assert_threads_equal( result[ u"threads" ][ 0 ], self.support_thread )

    assert result[ u"start" ] == 0
    assert result[ u"count" ] == 50
    assert result[ u"total_thread_count" ] == 1

  def test_unknown_forum( self ):
    result = self.http_get( "/forums/unknown/" )

    assert u"404" in result[ "body" ][ 0 ]

  def __make_extra_threads( self ):
    self.general_thread2 = Notebook.create( self.database.next_id( Notebook ), u"How does this thing work?" )
    self.database.save( self.general_thread2 )
    self.database.execute(
      self.anonymous.sql_save_notebook( self.general_thread2.object_id, read_write = Notebook.READ_WRITE_FOR_OWN_NOTES ),
    )
    self.database.execute(
      self.anonymous.sql_save_notebook_tag( self.general_thread2.object_id, self.forum_tag.object_id, value = u"general" ),
    )

    self.general_thread3 = Notebook.create( self.database.next_id( Notebook ), u"I have a problem with my pantalones." )
    self.database.save( self.general_thread3 )
    self.database.execute(
      self.anonymous.sql_save_notebook( self.general_thread3.object_id, read_write = Notebook.READ_WRITE_FOR_OWN_NOTES ),
    )
    self.database.execute(
      self.anonymous.sql_save_notebook_tag( self.general_thread3.object_id, self.forum_tag.object_id, value = u"general" ),
    )

  def test_general_several_threads( self ):
    self.__make_extra_threads()

    result = self.http_get( "/forums/general/" )

    assert result[ u"forum_name" ] == u"general"
    assert len( result[ u"threads" ] ) == 3

    self.__assert_threads_equal( result[ u"threads" ][ 0 ], self.general_thread3 )
    self.__assert_threads_equal( result[ u"threads" ][ 1 ], self.general_thread2 )
    self.__assert_threads_equal( result[ u"threads" ][ 2 ], self.general_thread )

    assert result[ u"start" ] == 0
    assert result[ u"count" ] == 50
    assert result[ u"total_thread_count" ] == 3

  def test_general_several_threads_with_start( self ):
    self.__make_extra_threads()

    result = self.http_get( "/forums/general/?start=1" )

    assert result[ u"forum_name" ] == u"general"
    assert len( result[ u"threads" ] ) == 2

    self.__assert_threads_equal( result[ u"threads" ][ 0 ], self.general_thread2 )
    self.__assert_threads_equal( result[ u"threads" ][ 1 ], self.general_thread )

    assert result[ u"start" ] == 1
    assert result[ u"count" ] == 50
    assert result[ u"total_thread_count" ] == 3

  def test_general_several_threads_with_count( self ):
    self.__make_extra_threads()

    result = self.http_get( "/forums/general/?count=2" )

    assert result[ u"forum_name" ] == u"general"
    assert len( result[ u"threads" ] ) == 2

    self.__assert_threads_equal( result[ u"threads" ][ 0 ], self.general_thread3 )
    self.__assert_threads_equal( result[ u"threads" ][ 1 ], self.general_thread2 )

    assert result[ u"start" ] == 0
    assert result[ u"count" ] == 2
    assert result[ u"total_thread_count" ] == 3

  def test_general_several_threads_with_start_and_count( self ):
    self.__make_extra_threads()

    result = self.http_get( "/forums/general/?start=1&count=1" )

    assert result[ u"forum_name" ] == u"general"
    assert len( result[ u"threads" ] ) == 1

    self.__assert_threads_equal( result[ u"threads" ][ 0 ], self.general_thread2 )

    assert result[ u"start" ] == 1
    assert result[ u"count" ] == 1
    assert result[ u"total_thread_count" ] == 3

  def test_general_thread_default( self ):
    result = self.http_get( "/forums/general/%s" % self.general_thread.object_id )

    assert result.get( u"user" ).object_id == self.anonymous.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"notebooks" )[ 0 ].object_id == self.anon_notebook.object_id
    assert result.get( u"login_url" )
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.general_thread.object_id
    assert len( result.get( u"startup_notes" ) ) == 0
    assert result.get( u"notes" ) == []
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert result.get( u"total_notes_count" ) == 0

    invites = result[ "invites" ]
    assert len( invites ) == 0

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_general_thread_default_with_login( self ):
    self.login()

    result = self.http_get(
      "/forums/general/%s" % self.general_thread.object_id,
      session_id = self.session_id,
    )

    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 4
    assert result.get( u"notebooks" )[ 0 ].object_id == self.notebook.object_id
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.general_thread.object_id
    assert len( result.get( u"startup_notes" ) ) == 0
    assert result.get( u"notes" ) == []
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert result.get( u"total_notes_count" ) == 0

    invites = result[ "invites" ]
    assert len( invites ) == 0

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_general_thread_default_with_unknown_thread_id( self ):
    path = "/forums/general/unknownthreadid"
    result = self.http_get( path )

    headers = result.get( "headers" )
    assert headers
    assert headers.get( "Location" ) == u"http:///login?after_login=%s" % urllib.quote( path )

  def __make_notes( self ):
    note_id = self.database.next_id( Note, commit = False )
    note = Note.create(
      note_id,
      u"<h3>foo</h3>bar",
      self.general_thread.object_id,
      startup = True,
      rank = 0,
      user_id = self.anonymous.object_id,
      creation = datetime.now(),
    )
    self.database.save( note, commit = False )
    self.note = note
    
    note_id = self.database.next_id( Note, commit = False )
    note = Note.create(
      note_id,
      u"<h3>bar</h3>baz",
      self.general_thread.object_id,
      startup = True,
      rank = 0,
      user_id = self.anonymous.object_id,
      creation = datetime.now(),
    )
    self.database.save( note, commit = False )

    note_id = self.database.next_id( Note, commit = False )
    note = Note.create(
      note_id,
      u"<h3>baz</h3>quux",
      self.general_thread.object_id,
      startup = True,
      rank = 0,
      user_id = self.anonymous.object_id,
      creation = datetime.now(),
    )
    self.database.save( note, commit = False )

    self.database.commit()

  def test_general_thread_default_with_notes( self ):
    self.__make_notes()

    result = self.http_get( "/forums/general/%s" % self.general_thread.object_id )

    assert result.get( u"user" ).object_id == self.anonymous.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"notebooks" )[ 0 ].object_id == self.anon_notebook.object_id
    assert result.get( u"login_url" )
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.general_thread.object_id
    assert len( result.get( u"startup_notes" ) ) == 3
    assert result[ u"startup_notes" ][ 0 ].title == u"foo"
    assert result[ u"startup_notes" ][ 1 ].title == u"bar"
    assert result[ u"startup_notes" ][ 2 ].title == u"baz"
    assert len( result.get( u"notes" ) ) == 3
    assert result[ u"notes" ][ 0 ].title == u"foo"
    assert result[ u"notes" ][ 1 ].title == u"bar"
    assert result[ u"notes" ][ 2 ].title == u"baz"
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert result.get( u"total_notes_count" ) == 3

    invites = result[ "invites" ]
    assert len( invites ) == 0

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_general_thread_default_with_notes_and_start( self ):
    self.__make_notes()

    result = self.http_get( "/forums/general/%s?start=1" % self.general_thread.object_id )

    assert result.get( u"user" ).object_id == self.anonymous.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"notebooks" )[ 0 ].object_id == self.anon_notebook.object_id
    assert result.get( u"login_url" )
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.general_thread.object_id
    assert len( result.get( u"startup_notes" ) ) == 3
    assert result[ u"startup_notes" ][ 0 ].title == u"foo"
    assert result[ u"startup_notes" ][ 1 ].title == u"bar"
    assert result[ u"startup_notes" ][ 2 ].title == u"baz"
    assert len( result.get( u"notes" ) ) == 2
    assert result[ u"notes" ][ 0 ].title == u"bar"
    assert result[ u"notes" ][ 1 ].title == u"baz"
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert result.get( u"total_notes_count" ) == 3

    invites = result[ "invites" ]
    assert len( invites ) == 0

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_general_thread_default_with_notes_and_count( self ):
    self.__make_notes()

    result = self.http_get( "/forums/general/%s?count=2" % self.general_thread.object_id )

    assert result.get( u"user" ).object_id == self.anonymous.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"notebooks" )[ 0 ].object_id == self.anon_notebook.object_id
    assert result.get( u"login_url" )
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.general_thread.object_id
    assert len( result.get( u"startup_notes" ) ) == 3
    assert result[ u"startup_notes" ][ 0 ].title == u"foo"
    assert result[ u"startup_notes" ][ 1 ].title == u"bar"
    assert result[ u"startup_notes" ][ 2 ].title == u"baz"
    assert len( result.get( u"notes" ) ) == 2
    assert result[ u"notes" ][ 0 ].title == u"foo"
    assert result[ u"notes" ][ 1 ].title == u"bar"
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert result.get( u"total_notes_count" ) == 3

    invites = result[ "invites" ]
    assert len( invites ) == 0

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_general_thread_default_with_notes_and_start_and_count( self ):
    self.__make_notes()

    result = self.http_get( "/forums/general/%s?start=1&count=1" % self.general_thread.object_id )

    assert result.get( u"user" ).object_id == self.anonymous.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"notebooks" )[ 0 ].object_id == self.anon_notebook.object_id
    assert result.get( u"login_url" )
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.general_thread.object_id
    assert len( result.get( u"startup_notes" ) ) == 3
    assert result[ u"startup_notes" ][ 0 ].title == u"foo"
    assert result[ u"startup_notes" ][ 1 ].title == u"bar"
    assert result[ u"startup_notes" ][ 2 ].title == u"baz"
    assert len( result.get( u"notes" ) ) == 1
    assert result[ u"notes" ][ 0 ].title == u"bar"
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert result.get( u"total_notes_count" ) == 3

    invites = result[ "invites" ]
    assert len( invites ) == 0

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_general_thread_default_with_notes_and_note_id( self ):
    self.__make_notes()

    result = self.http_get( "/forums/general/%s?note_id=%s" % ( self.general_thread.object_id, self.note.object_id ) )

    assert result.get( u"user" ).object_id == self.anonymous.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"notebooks" )[ 0 ].object_id == self.anon_notebook.object_id
    assert result.get( u"login_url" )
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.general_thread.object_id
    assert len( result.get( u"startup_notes" ) ) == 3
    assert result[ u"startup_notes" ][ 0 ].title == u"foo"
    assert result[ u"startup_notes" ][ 1 ].title == u"bar"
    assert result[ u"startup_notes" ][ 2 ].title == u"baz"
    assert len( result.get( u"notes" ) ) == 1
    assert result[ u"notes" ][ 0 ].title == u"foo"
    assert result[ u"notes" ][ 0 ].object_id == self.note.object_id
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert result.get( u"total_notes_count" ) == 3

    invites = result[ "invites" ]
    assert len( invites ) == 0

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def __assert_new_forum_thread( self, thread, expected_id ):
    assert thread
    assert thread.object_id == expected_id
    assert thread.name == u"new discussion"
    assert thread.trash_id is None
    assert thread.read_write == Notebook.READ_WRITE_FOR_OWN_NOTES
    assert thread.owner == False
    assert thread.deleted == False
    assert thread.user_id == self.user.object_id

  def test_general_create_thread( self ):
    self.login()

    result = self.http_get(
      "/forums/general/create_thread",
      session_id = self.session_id,
    )

    redirect = result.get( u"redirect" )
    assert redirect
    assert redirect.startswith( u"/forums/general/" )
    new_thread_id = redirect.split( "/forums/general/" )[ -1 ].split( u"?" )[ 0 ]

    thread = cherrypy.root.users.load_notebook( self.user.object_id, new_thread_id, read_write = True )
    self.__assert_new_forum_thread( thread, new_thread_id )
    tags = self.database.select_many( Tag, thread.sql_load_tags( self.user.object_id ) )
    assert tags == []

    thread = cherrypy.root.users.load_notebook( self.anonymous.object_id, new_thread_id, read_write = False )
    self.__assert_new_forum_thread( thread, new_thread_id )
    tags = self.database.select_many( Tag, thread.sql_load_tags( self.anonymous.object_id ) )

    assert tags
    assert len( tags ) == 1
    assert tags[ 0 ].name == u"forum"
    assert tags[ 0 ].value == u"general"

    notes = self.database.select_many( Note, thread.sql_load_notes() )
    assert notes
    assert len( notes ) == 1
    assert notes[ 0 ].title == None
    assert notes[ 0 ].contents == u"<h3>"
    assert notes[ 0 ].notebook_id == thread.object_id
    assert notes[ 0 ].startup is True
    assert notes[ 0 ].deleted_from_id is None
    assert notes[ 0 ].rank == 0
    assert notes[ 0 ].user_id == self.user.object_id

  def test_general_create_thread_without_login( self ):
    path = "/forums/general/create_thread"
    result = self.http_get( path )

    headers = result.get( "headers" )
    assert headers
    assert headers.get( "Location" ) == u"http:///login?after_login=%s" % urllib.quote( path )

  def login( self ):
    result = self.http_post( "/users/login", dict(
      username = self.username,
      password = self.password,
      login_button = u"login",
    ) )
    self.session_id = result[ u"session_id" ]

  def login2( self ):
    result = self.http_post( "/users/login", dict(
      username = self.username2,
      password = self.password2,
      login_button = u"login",
    ) )
    self.session_id = result[ u"session_id" ]
