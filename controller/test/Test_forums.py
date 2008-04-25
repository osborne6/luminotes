import cherrypy
from model.Note import Note
from model.Notebook import Notebook
from model.User import User
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

  def test_index( self ):
    result = self.http_get( "/forums/" )

    assert result
    assert result.get( u"redirect" ) is None
    assert result[ u"user" ].username == u"anonymous"
    assert len( result[ u"notebooks" ] ) == 1
    assert result[ u"first_notebook" ] == None
    assert result[ u"login_url" ] == u"https://luminotes.com/notebooks/%s?note_id=%s" % (
      self.anon_notebook.object_id, self.login_note.object_id,
    )
    assert result[ u"logout_url" ] == u"https://luminotes.com/users/logout"
    assert result[ u"rate_plan" ]
