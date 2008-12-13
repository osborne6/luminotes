import re
from Persistent import Persistent, quote
from controller.Html_nuker import Html_nuker


class Note( Persistent ):
  """
  An single textual wiki note.
  """
  TITLE_PATTERN = re.compile( u"<h3>(.*?)</h3>", flags = re.IGNORECASE )

  def __init__( self, object_id, revision = None, title = None, contents = None, notebook_id = None,
                startup = None, deleted_from_id = None, rank = None, user_id = None,
                username = None, creation = None, summary = None ):
    """
    Create a new note with the given id and contents.

    @type object_id: unicode
    @param object_id: id of the note
    @type revision: datetime or NoneType
    @param revision: revision timestamp of the object (optional, defaults to now)
    @type title: unicode or NoneType
    @param title: textual title of the note (optional, defaults to derived from contents)
    @type contents: unicode or NoneType
    @param contents: HTML contents of the note (optional)
    @type notebook_id: unicode or NoneType
    @param notebook_id: id of notebook containing this note (optional)
    @type startup: bool or NoneType
    @param startup: whether this note should be displayed upon startup (optional, defaults to False)
    @type deleted_from_id: unicode or NoneType
    @param deleted_from_id: id of the notebook that this note was deleted from (optional)
    @type rank: float or NoneType
    @param rank: indicates numeric ordering of this note in relation to other startup notes
    @type user_id: unicode or NoneType
    @param user_id: id of the user who most recently updated this note object (optional)
    @type username: unicode or NoneType
    @param username: username of the user who most recently updated this note object (optional)
    @type creation: datetime or NoneType
    @param creation: creation timestamp of the object (optional, defaults to None)
    @type summary: unicode or NoneType
    @param summary: textual summary of the note's contents (optional, defaults to None)
    @rtype: Note
    @return: newly constructed note
    """
    Persistent.__init__( self, object_id, revision )
    self.__title = title
    self.__contents = contents
    self.__summary = summary
    self.__notebook_id = notebook_id
    self.__startup = startup or False
    self.__deleted_from_id = deleted_from_id
    self.__rank = rank
    self.__user_id = user_id
    self.__username = username
    self.__creation = creation

  @staticmethod
  def create( object_id, contents = None, notebook_id = None, startup = None, rank = None,
              user_id = None, username = None, creation = None, summary = None ):
    """
    Convenience constructor for creating a new note.

    @type object_id: unicode
    @param object_id: id of the note
    @type contents: unicode or NoneType
    @param contents: HTML contents of the note (optional)
    @type notebook_id: unicode or NoneType
    @param notebook_id: id of notebook containing this note (optional)
    @type startup: bool or NoneType
    @param startup: whether this note should be displayed upon startup (optional, defaults to False)
    @type rank: float or NoneType
    @param rank: indicates numeric ordering of this note in relation to other startup notes
    @type user_id: unicode or NoneType
    @param user_id: id of the user who most recently updated this note object (optional)
    @type username: unicode or NoneType
    @param username: username of the user who most recently updated this note object (optional)
    @type creation: datetime or NoneType
    @param creation: creation timestamp of the object (optional, defaults to None)
    @type summary: unicode or NoneType
    @param summary: textual summary of the note's contents (optional, defaults to None)
    @rtype: Note
    @return: newly constructed note
    """
    note = Note(
      object_id, notebook_id = notebook_id, startup = startup, rank = rank, user_id = user_id,
      username = username, creation = creation, summary = summary
    )

    note.contents = contents

    return note

  def __set_contents( self, contents ):
    self.update_revision()
    self.__contents = contents

    if contents is None:
      self.__title = None
      return

    # parse title out of the beginning of the contents
    result = Note.TITLE_PATTERN.search( contents )

    if result:
      self.__title = result.groups()[ 0 ]
      self.__title = Html_nuker( allow_refs = True ).nuke( self.__title )
    else:
      self.__title = None

  def replace_contents( self, contents ):
    self.__contents = contents

  def __set_summary( self, summary ):
    self.__summary = summary

  def __set_notebook_id( self, notebook_id ):
    self.__notebook_id = notebook_id
    self.update_revision()

  def __set_startup( self, startup ):
    self.__startup = startup
    self.update_revision()

  def __set_deleted_from_id( self, deleted_from_id ):
    self.__deleted_from_id = deleted_from_id
    self.update_revision()

  def __set_rank( self, rank ):
    self.__rank = rank
    self.update_revision()

  def __set_user_id( self, user_id ):
    self.__user_id = user_id
    self.update_revision()

  @staticmethod
  def sql_load( object_id, revision = None ):
    if revision:
      return "select id, revision, title, contents, notebook_id, startup, deleted_from_id, rank, user_id from note where id = %s and revision = %s;" % ( quote( object_id ), quote( revision ) )

    return "select id, revision, title, contents, notebook_id, startup, deleted_from_id, rank, user_id from note_current where id = %s;" % quote( object_id )

  @staticmethod
  def sql_id_exists( object_id, revision = None ):
    if revision:
      return "select id from note where id = %s and revision = %s;" % ( quote( object_id ), quote( revision ) )

    return "select id from note_current where id = %s;" % quote( object_id )

  def sql_exists( self ):
    return Note.sql_id_exists( self.object_id )

  def sql_create( self ):
    rank = self.__rank
    if rank is None:
      rank = quote( None )

    # this relies on a database trigger to copy the new row into the note table
    return \
      "insert into note_current ( id, revision, title, contents, notebook_id, startup, deleted_from_id, rank, user_id ) " + \
      "values ( %s, %s, %s, %s, %s, %s, %s, %s, %s );" % \
      ( quote( self.object_id ), quote( self.revision ), quote( self.__title ),
        quote( self.__contents ), quote( self.__notebook_id ), quote( self.__startup and 't' or 'f' ),
        quote( self.__deleted_from_id ), rank, quote( self.user_id ) )

  def sql_update( self ):
    rank = self.__rank
    if rank is None:
      rank = quote( None )

    # this relies on a database trigger to copy the updated row into the note table
    return \
      """
      update note_current set id = %s, revision = %s, title = %s, contents = %s, notebook_id = %s,
      startup = %s, deleted_from_id = %s, rank = %s, user_id = %s where id = %s;
      """ % \
      ( quote( self.object_id ), quote( self.revision ), quote( self.__title ),
        quote( self.__contents ), quote( self.__notebook_id ), quote( self.__startup and 't' or 'f' ),
        quote( self.__deleted_from_id ), rank, quote( self.user_id ), quote( self.object_id ) )

  def sql_load_revisions( self ):
    return """ \
      select
        note.revision, luminotes_user_current.id, username
      from
        note left outer join luminotes_user_current
      on
        ( note.user_id = luminotes_user_current.id )
      where
        note.id = %s order by note.revision;
    """ % quote( self.object_id )

  def to_dict( self ):
    d = Persistent.to_dict( self )
    d.update( dict(
      contents = self.__contents,
      summary = self.__summary,
      notebook_id = self.__notebook_id,
      title = self.__title,
      deleted_from_id = self.__deleted_from_id,
      user_id = self.__user_id,
      username = self.__username,
      creation = self.__creation,
    ) )

    return d

  title = property( lambda self: self.__title )
  contents = property( lambda self: self.__contents, __set_contents )
  summary = property( lambda self: self.__summary, __set_summary )
  notebook_id = property( lambda self: self.__notebook_id, __set_notebook_id )
  startup = property( lambda self: self.__startup, __set_startup )
  deleted_from_id = property( lambda self: self.__deleted_from_id, __set_deleted_from_id )
  rank = property( lambda self: self.__rank, __set_rank )
  user_id = property( lambda self: self.__user_id, __set_user_id )
  username = property( lambda self: self.__username )
  creation = property( lambda self: self.__creation )
