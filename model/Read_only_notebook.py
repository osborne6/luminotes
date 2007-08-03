from Persistent import Persistent


class Read_only_notebook( Persistent ):
  """
  A wrapper for Notebook that hides all of its destructive update functions.
  """
  def __init__( self, id, notebook ):
    Persistent.__init__( self, id )
    self.__wrapped = notebook

  def lookup_note( self, note_id ):
    return self.__wrapped.lookup_note( note_id )

  def lookup_note_by_title( self, title ):
    return self.__wrapped.lookup_note_by_title( title )

  def to_dict( self ):
    d = self.__wrapped.to_dict()
    del( d[ "trash" ] ) # don't expose the trash to read-only views of this notebook
    d.update( dict(
      object_id = self.object_id,
      read_write = False,
    ) )

    return d

  name = property( lambda self: self.__wrapped.name )
  trash = None # read-only access doesn't give you access to the Notebook's trash
  notes = property( lambda self: self.__wrapped.notes )
  startup_notes = property( lambda self: self.__wrapped.startup_notes )
