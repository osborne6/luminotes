import re
from copy import copy
from Note import Note
from Persistent import Persistent, quote, quote_fuzzy


class Notebook( Persistent ):
  """
  A collection of wiki notes.
  """

  WHITESPACE_PATTERN = re.compile( r"\s+" )
  SEARCH_OPERATORS = re.compile( r"[&|!()'\\:]" )

  READ_ONLY = 0                # user can only view the notes within this notebook
  READ_WRITE = 1               # user can view and edit the notes within this notebook
  READ_WRITE_FOR_OWN_NOTES = 2 # user can only edit their own notes, not notes created by others

  def __init__( self, object_id, revision = None, name = None, trash_id = None, deleted = False,
                user_id = None, read_write = None, owner = True, rank = None, own_notes_only = False ):
    """
    Create a new notebook with the given id and name.

    @type object_id: unicode
    @param object_id: id of the notebook
    @type revision: datetime or NoneType
    @param revision: revision timestamp of the object (optional, defaults to now)
    @type name: unicode or NoneType
    @param name: name of this notebook (optional)
    @type trash_id: Notebook or NoneType
    @param trash_id: id of the notebook where deleted notes from this notebook go to die (optional)
    @type deleted: bool or NoneType
    @param deleted: whether this notebook is currently deleted (optional, defaults to False)
    @type user_id: unicode or NoneType
    @param user_id: id of the user who most recently updated this notebook object (optional)
    @type read_write: bool or NoneType
    @param read_write: whether this view of the notebook is currently read-write. one of:
                       READ_ONLY, READ_WRITE, READ_WRITE_FOR_OWN_NOTES (optional, defaults to READ_WRITE)
    @type owner: bool or NoneType
    @param owner: whether this view of the notebook currently has owner-level access (optional, defaults to True)
    @type rank: float or NoneType
    @param rank: indicates numeric ordering of this note in relation to other notebooks
    @type own_notes_only: bool or NoneType
    @param own_notes_only: True makes read_write be READ_WRITE_FOR_OWN_NOTES (optional, defaults to False)
    @rtype: Notebook
    @return: newly constructed notebook
    """
    Persistent.__init__( self, object_id, revision )
    self.__name = name
    self.__trash_id = trash_id
    self.__deleted = deleted
    self.__user_id = user_id

    read_write = {
      None: Notebook.READ_WRITE,
      True: Notebook.READ_WRITE,
      False: Notebook.READ_ONLY,
    }.get( read_write, read_write )

    if own_notes_only is True and read_write != Notebook.READ_ONLY:
      read_write = Notebook.READ_WRITE_FOR_OWN_NOTES

    self.__read_write = read_write
    self.__owner = owner
    self.__rank = rank

  @staticmethod
  def create( object_id, name = None, trash_id = None, deleted = False, user_id = None, read_write = None, owner = True, rank = None, own_notes_only = False ):
    """
    Convenience constructor for creating a new notebook.

    @type object_id: unicode
    @param object_id: id of the notebook
    @type name: unicode or NoneType
    @param name: name of this notebook (optional)
    @type trash_id: Notebook or NoneType
    @param trash_id: id of the notebook where deleted notes from this notebook go to die (optional)
    @type deleted: bool or NoneType
    @param deleted: whether this notebook is currently deleted (optional, defaults to False)
    @type user_id: unicode or NoneType
    @param user_id: id of the user who most recently updated this notebook object (optional)
    @type read_write: bool or NoneType
    @param read_write: whether this view of the notebook is currently read-write. one of:
                       READ_ONLY, READ_WRITE, READ_WRITE_FOR_OWN_NOTES (optional, defaults to READ_WRITE)
    @type owner: bool or NoneType
    @param owner: whether this view of the notebook currently has owner-level access (optional, defaults to True)
    @type rank: float or NoneType
    @param rank: indicates numeric ordering of this note in relation to other notebooks
    @type own_notes_only: bool or NoneType
    @param own_notes_only: True makes read_write be READ_WRITE_FOR_OWN_NOTES (optional, defaults to False)
    @rtype: Notebook
    @return: newly constructed notebook
    """
    return Notebook( object_id, name = name, trash_id = trash_id, user_id = user_id, read_write = read_write, owner = owner, rank = rank, own_notes_only = own_notes_only )

  @staticmethod
  def sql_load( object_id, revision = None ):
    if revision:
      return "select * from notebook where id = %s and revision = %s;" % ( quote( object_id ), quote( revision ) )

    return "select * from notebook_current where id = %s;" % quote( object_id )

  @staticmethod
  def sql_id_exists( object_id, revision = None ):
    if revision:
      return "select id from notebook where id = %s and revision = %s;" % ( quote( object_id ), quote( revision ) )

    return "select id from notebook_current where id = %s;" % quote( object_id )

  def sql_exists( self ):
    return Notebook.sql_id_exists( self.object_id, self.revision )

  def sql_create( self ):
    return \
      "insert into notebook ( id, revision, name, trash_id, deleted, user_id ) " + \
      "values ( %s, %s, %s, %s, %s, %s );" % \
      ( quote( self.object_id ), quote( self.revision ), quote( self.__name ),
        quote( self.__trash_id ), quote( self.deleted ), quote( self.user_id ) )

  def sql_update( self ):
    return self.sql_create()

  def sql_load_notes( self, start = 0, count = None ):
    """
    Return a SQL string to load a list of all the notes within this notebook.
    Note: If the database backend is SQLite, a start parameter cannot be given without also
    providing a count parameter.
    """
    if count is not None:
      limit_clause = " limit %s" % count
    else:
      limit_clause = ""

    if start:
      offset_clause = " offset %s" % start
    else:
      offset_clause = ""

    return "select id, revision, title, contents, notebook_id, startup, deleted_from_id, rank, user_id from note_current where notebook_id = %s order by revision desc%s%s;" % ( quote( self.object_id ), limit_clause, offset_clause )

  def sql_load_non_startup_notes( self ):
    """
    Return a SQL string to load a list of the non-startup notes within this notebook.
    """
    return "select id, revision, title, contents, notebook_id, startup, deleted_from_id, rank, user_id from note_current where notebook_id = %s and startup = 'f' order by revision desc;" % quote( self.object_id )

  def sql_load_startup_notes( self ):
    """
    Return a SQL string to load a list of the startup notes within this notebook.
    """
    return "select id, revision, title, contents, notebook_id, startup, deleted_from_id, rank, user_id from note_current where notebook_id = %s and startup = 't' order by rank;" % quote( self.object_id )

  def sql_load_recent_notes( self, start = 0, count = 10 ):
    """
    Return a SQL string to load a list of the most recently created notes within this notebook.

    @type start: int or NoneType
    @param start: index of recent note to start with (defaults to 0, the most recent note)
    @type count: int or NoneType
    @param count: number of recent notes to return (defaults to 10 notes)
    """
    return \
      """
      select
        note_current.id, note_current.revision, note_current.title, note_current.contents,
        note_current.notebook_id, note_current.startup, note_current.deleted_from_id,
        note_current.rank, note_current.user_id, note_creation.revision as creation
      from
        note_current,
        ( select id, min( revision ) as revision from note where notebook_id = %s group by id ) as note_creation
      where
        notebook_id = %s and note_current.id = note_creation.id
      order by
        creation desc
      limit %d offset %d;
      """ % ( quote( self.object_id ), quote( self.object_id ), count, start )

  def sql_load_note_by_id( self, note_id ):
    """
    Return a SQL string to load a particular note within this notebook by the note's id.

    @type note_id: unicode
    @param note_id: id of note to load
    """
    return "select id, revision, title, contents, notebook_id, startup, deleted_from_id, rank, user_id from note_current where notebook_id = %s and id = %s;" % ( quote( self.object_id ), quote( note_id ) )

  def sql_load_note_by_title( self, title ):
    """
    Return a SQL string to load a particular note within this notebook by the note's title. The
    title lookup is performed case-insensitively.

    @type note_id: unicode
    @param note_id: title of note to load
    """
    return "select id, revision, title, contents, notebook_id, startup, deleted_from_id, rank, user_id from note_current where notebook_id = %s and lower( title ) = lower( %s );" % ( quote( self.object_id ), quote( title ) )

  @staticmethod
  def sql_search_notes( user_id, first_notebook_id, search_text, database_backend ):
    """
    Return a SQL string to perform a full-text search for notes within notebooks readable by the
    given user whose contents contain the given search_text. This is a case-insensitive search.

    @type search_text: unicode
    @param search_text: text to search for within the notes
    """
    if database_backend == Persistent.POSTGRESQL_BACKEND:
      # strip out all search operators
      search_text = Notebook.SEARCH_OPERATORS.sub( u"", search_text ).strip()

      # join all words with boolean "and" operator
      search_text = u"&".join( Notebook.WHITESPACE_PATTERN.split( search_text ) )

      return \
        """
        select id, revision, title, contents, notebook_id, startup, deleted_from_id, rank, user_id, null,
               headline( drop_html_tags( contents ), query ) as summary from (
          select
            note_current.id, note_current.revision, note_current.title, note_current.contents,
            note_current.notebook_id, note_current.startup, note_current.deleted_from_id,
            rank_cd( search, query ) as rank, note_current.user_id, null, query
          from
            note_current, user_notebook, to_tsquery( 'default', %s ) query
          where
            note_current.notebook_id = user_notebook.notebook_id and user_notebook.user_id = %s and
            note_current.deleted_from_id is null and
            query @@ search order by note_current.notebook_id = %s desc, rank desc limit 20
        ) as sub;
        """ % ( quote( search_text ), quote( user_id ),
                quote( first_notebook_id ) )
    else:
      search_text = search_text.strip().lower()

      # TODO: use SQLite's FTS (full text search) support instead
      return \
        """
        select
          note_current.*
        from
          note_current, user_notebook
        where
          note_current.notebook_id = user_notebook.notebook_id and user_notebook.user_id = %s and
          note_current.deleted_from_id is null and
          lower( note_current.contents ) like %s
          order by note_current.notebook_id = %s desc, note_current.rank desc limit 20
        """ % ( quote( user_id ), quote_fuzzy( search_text ), quote( first_notebook_id ) )

  @staticmethod
  def sql_search_titles( notebook_id, search_text ):
    """
    Return a SQL string to perform a search for notes within the given notebook whose titles contain
    the given search_text. This is a case-insensitive search.

    @type search_text: unicode
    @param search_text: text to search for within the notes
    """
    search_text = search_text.strip()

    return \
      """
      select id, revision, title, contents, notebook_id, startup, deleted_from_id, rank, user_id, null,
             title as summary
      from
        note_current
      where
        notebook_id = %s and
        deleted_from_id is null and
        lower( title ) like %s
      order by
        revision desc limit 20;
      """ % ( quote( notebook_id ), 
              quote_fuzzy( search_text.lower() ) )

  def sql_highest_note_rank( self ):
    """
    Return a SQL string to determine the highest numbered rank of all notes in this notebook."
    """
    return "select coalesce( max( rank ), -1 ) from note_current where notebook_id = %s;" % quote( self.object_id )

  def sql_count_notes( self ):
    """
    Return a SQL string to count the total number of notes in this notebook.
    """
    return \
      "select count( id ) from note_current where notebook_id = %s;" % \
      ( quote( self.object_id ) )

  def sql_load_tag_by_name( self, user_id, tag_name ):
    """
    Return a SQL string to load a tag associated with this notebook by the given user.
    """
    return \
      """
      select
        tag.id, tag.revision, tag.notebook_id, tag.user_id, tag.name, tag.description, tag_notebook.value
      from
        tag_notebook, tag
      where
        tag_notebook.notebook_id = %s and 
        tag_notebook.user_id = %s and
        tag_notebook.tag_id = tag.id and
        tag.name = %s
      order by tag.name;
      """ % ( quote( self.object_id ), quote( user_id ), quote( tag_name ) )

  def sql_load_tags( self, user_id ):
    """
    Return a SQL string to load a list of all the tags associated with this notebook by the given
    user.
    """
    return \
      """
      select
        tag.id, tag.revision, tag.notebook_id, tag.user_id, tag.name, tag.description, tag_notebook.value
      from
        tag_notebook, tag
      where
        tag_notebook.notebook_id = %s and 
        tag_notebook.user_id = %s and
        tag_notebook.tag_id = tag.id
      order by tag.name;
      """ % ( quote( self.object_id ), quote( user_id ) )

  def to_dict( self ):
    d = Persistent.to_dict( self )

    d.update( dict(
      name = self.__name,
      trash_id = self.__trash_id,
      read_write = self.__read_write,
      owner = self.__owner,
      deleted = self.__deleted,
      user_id = self.__user_id,
    ) )

    return d

  def __set_name( self, name ):
    self.__name = name
    self.update_revision()

  def __set_read_write( self, read_write ):
    # The read_write member isn't actually saved to the database, so setting it doesn't need to
    # call update_revision().
    read_write = {
      None: Notebook.READ_WRITE,
      True: Notebook.READ_WRITE,
      False: Notebook.READ_ONLY,
    }.get( read_write, read_write )

    self.__read_write = read_write

  def __set_owner( self, owner ):
    # The owner member isn't actually saved to the database, so setting it doesn't need to
    # call update_revision().
    self.__owner = owner

  def __set_deleted( self, deleted ):
    self.__deleted = deleted
    self.update_revision()

  def __set_user_id( self, user_id ):
    self.__user_id = user_id
    self.update_revision()

  def __set_rank( self, rank ):
    # The rank member isn't actually saved to the database, so setting it doesn't need to
    # call update_revision().
    self.__rank = rank

  name = property( lambda self: self.__name, __set_name )
  trash_id = property( lambda self: self.__trash_id )
  read_write = property( lambda self: self.__read_write, __set_read_write )
  owner = property( lambda self: self.__owner, __set_owner )
  deleted = property( lambda self: self.__deleted, __set_deleted )
  user_id = property( lambda self: self.__user_id, __set_user_id )
  rank = property( lambda self: self.__rank, __set_rank )
