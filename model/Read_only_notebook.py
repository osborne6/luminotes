from Persistent import Persistent


class Read_only_notebook( Persistent ):
  """
  A wrapper for Notebook that hides all of its destructive update functions.
  """
  def __init__( self, id, notebook ):
    Persistent.__init__( self, id )
    self.__wrapped = notebook

  def lookup_entry( self, entry_id ):
    return self.__wrapped.lookup_entry( entry_id )

  def lookup_entry_by_title( self, title ):
    return self.__wrapped.lookup_entry_by_title( title )

  def to_dict( self ):
    d = self.__wrapped.to_dict()
    d.update( dict(
      object_id = self.object_id,
      read_write = False,
    ) )

    return d

  name = property( lambda self: self.__wrapped.name )
  entries = property( lambda self: self.__wrapped.entries )
  startup_entries = property( lambda self: self.__wrapped.startup_entries )
