import re
from Persistent import Persistent
from controller.Html_nuker import Html_nuker


class Note( Persistent ):
  """
  An single textual wiki note.
  """
  TITLE_PATTERN = re.compile( u"<h3>(.*)</h3>", flags = re.IGNORECASE )

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

    self.__set_contents( contents )

  def __set_contents( self, contents ):
    self.update_revision()
    self.__contents = contents

    # parse title out of the beginning of the contents
    result = Note.TITLE_PATTERN.search( contents )

    if result:
      self.__title = result.groups()[ 0 ]
      self.__title = Html_nuker( allow_refs = True ).nuke( self.__title )
    else:
      self.__title = None

  def to_dict( self ):
    d = Persistent.to_dict( self )
    d.update( dict(
      contents = self.__contents,
      title = self.__title,
    ) )

    return d

  contents = property( lambda self: self.__contents, __set_contents )
  title = property( lambda self: self.__title )
