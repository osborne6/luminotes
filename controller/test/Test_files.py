import types
import cherrypy
from Test_controller import Test_controller
from model.Notebook import Notebook
from model.Note import Note
from model.User import User
from model.Invite import Invite
from controller.Notebooks import Access_error


class Test_files( Test_controller ):
  def setUp( self ):
    Test_controller.setUp( self )

    self.notebook = None
    self.anon_notebook = None
    self.username = u"mulder"
    self.password = u"trustno1"
    self.email_address = u"outthere@example.com"
    self.username2 = u"deepthroat"
    self.password2 = u"mmmtobacco"
    self.email_address2 = u"parkinglot@example.com"
    self.user = None
    self.user2 = None
    self.anonymous = None
    self.session_id = None
    self.filename = "file.png"
    self.file_data = "foobar\x07`-=[]\;',./~!@#$%^&*()_+{}|:\"<>?" * 100

    self.make_users()
    self.make_notebooks()
    self.database.commit()

  def make_notebooks( self ):
    user_id = self.user.object_id

    self.trash = Notebook.create( self.database.next_id( Notebook ), u"trash", user_id = user_id )
    self.database.save( self.trash, commit = False )
    self.notebook = Notebook.create( self.database.next_id( Notebook ), u"notebook", self.trash.object_id, user_id = user_id )
    self.database.save( self.notebook, commit = False )

    note_id = self.database.next_id( Note )
    self.note = Note.create( note_id, u"<h3>my title</h3>blah", notebook_id = self.notebook.object_id, startup = True, user_id = user_id )
    self.database.save( self.note, commit = False )

    self.anon_notebook = Notebook.create( self.database.next_id( Notebook ), u"anon_notebook", user_id = user_id )
    self.database.save( self.anon_notebook, commit = False )

    self.database.execute( self.user.sql_save_notebook( self.notebook.object_id, read_write = True, owner = True ) )
    self.database.execute( self.user.sql_save_notebook( self.notebook.trash_id, read_write = True, owner = True ) )
    self.database.execute( self.user.sql_save_notebook( self.anon_notebook.object_id, read_write = False, owner = False ) )

  def make_users( self ):
    self.user = User.create( self.database.next_id( User ), self.username, self.password, self.email_address )
    self.database.save( self.user, commit = False )

    self.user2 = User.create( self.database.next_id( User ), self.username2, self.password2, self.email_address2 )
    self.database.save( self.user2, commit = False )

    self.anonymous = User.create( self.database.next_id( User ), u"anonymous" )
    self.database.save( self.anonymous, commit = False )

  def test_upload_page( self ):
    result = self.http_get(
      "/files/upload_page?notebook_id=%s&note_id=%s" % ( self.notebook.object_id, self.note.object_id ),
    )

    assert result.get( u"notebook_id" ) == self.notebook.object_id
    assert result.get( u"note_id" ) == self.note.object_id

  def test_upload( self ):
    self.login()

    result = self.http_upload(
      "/files/upload",
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      session_id = self.session_id,
    )

    gen = result[ u"body" ]
    assert isinstance( gen, types.GeneratorType )

    tick_count = 0
    tick_done = False

    try:
      for piece in gen:
        if u"tick(" in piece:
          tick_count += 1
        if u"tick(1.0)" in piece:
          tick_done = True
    # during this unit test, full session info isn't available, so swallow an expected
    # exception about session_storage
    except AttributeError, exc:
      if u"session_storage" not in str( exc ):
        raise exc

    # assert that the progress bar is moving, and then completes
    assert tick_count >= 2
    assert tick_done

    # TODO: assert that the uploaded file actually got stored somewhere

  def test_upload_without_login( self ):
    result = self.http_upload(
      "/files/upload",
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      session_id = self.session_id,
    )

    assert u"access" in result.get( u"body" )[ 0 ]

  def test_upload_without_access( self ):
    self.login2()

    result = self.http_upload(
      "/files/upload",
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      session_id = self.session_id,
    )

    assert u"access" in result.get( u"body" )[ 0 ]

  def assert_streaming_error( self, result ):
    gen = result[ u"body" ]
    assert isinstance( gen, types.GeneratorType )

    found_error = False

    try:
      for piece in gen:
        if "error" in piece:
          found_error = True
    except AttributeError, exc:
      if u"session_storage" not in str( exc ):
        raise exc

    assert found_error

  def test_upload_unnamed( self ):
    self.login()

    result = self.http_upload(
      "/files/upload",
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = "",
      file_data = self.file_data,
      session_id = self.session_id,
    )

    self.assert_streaming_error( result )

  def test_upload_empty( self ):
    self.login()

    result = self.http_upload(
      "/files/upload",
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = "",
      session_id = self.session_id,
    )

    self.assert_streaming_error( result )

  def test_upload_invalid_content_length( self ):
    self.login()

    result = self.http_upload(
      "/files/upload",
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      headers = [ ( "Content-Length", "-10" ) ],
      session_id = self.session_id,
    )

    assert "invalid" in result[ "body" ][ 0 ]

  def test_upload_cancel( self ):
    self.login()

    result = self.http_upload(
      "/files/upload",
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      simulate_cancel = True,
      session_id = self.session_id,
    )

    self.assert_streaming_error( result )

  def test_upload_over_quota( self ):
    raise NotImplementError()

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
