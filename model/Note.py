import re
from Persistent import Persistent
from controller.Html_nuker import Html_nuker


class Note( Persistent ):
  """
  An single textual wiki note.
  """
  TITLE_PATTERN = re.compile( u"<h3>(.*)</h3>", flags = re.IGNORECASE )

  def __setstate__( self, state ):
    if "_Note__deleted_from" not in state:
      state[ "_Note__deleted_from" ] = False

    self.__dict__.update( state )

  def __init__( self, id, contents = None ):
    """
    Create a new note with the given id and contents.

    @type id: unicode
    @param id: id of the note
    @type contents: unicode or NoneType
    @param contents: initial contents of the note (optional)
    @rtype: Note
    @return: newly constructed note
    """
    Persistent.__init__( self, id )
    self.__title = None
    self.__contents = None or ""
    self.__deleted_from = None

    self.__set_contents( contents, new_revision = False )

  def __set_contents( self, contents, new_revision = True ):
    if new_revision:
      self.update_revision()
    self.__contents = contents

    # parse title out of the beginning of the contents
    result = Note.TITLE_PATTERN.search( contents )

    if result:
      self.__title = result.groups()[ 0 ]
      self.__title = Html_nuker( allow_refs = True ).nuke( self.__title )
    else:
      self.__title = None

  def __set_deleted_from( self, deleted_from ):
    self.__deleted_from = deleted_from
    self.update_revision()

  def to_dict( self ):
    d = Persistent.to_dict( self )
    d.update( dict(
      contents = self.__contents,
      title = self.__title,
      deleted_from = self.__deleted_from,
    ) )

    return d

  contents = property( lambda self: self.__contents, __set_contents )
  title = property( lambda self: self.__title )
  deleted_from = property( lambda self: self.__deleted_from, __set_deleted_from )
