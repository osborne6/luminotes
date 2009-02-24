import os.path
from model.Persistent import Persistent


class Schema_upgrader:
  def __init__( self, database, glob = None, read_file = None ):
    """
    Create a new schema upgrader and return it.

    @type database: Database
    @param database: the database to use for all schema upgrades
    @type glob: function or NoneType
    @param glob: a custom function to use for globbing files as per glob.glob() (optional)
    @type read_file: function or NoneType
    @param read_file: a custom function to use for reading schema files (optional)
    @rtype: Schema_upgrader
    @return: newly constructed Schema_upgrader
    """
    from glob import glob as real_glob

    self.__database = database
    self.__glob = glob or real_glob
    self.__read_file = read_file or Schema_upgrader.__read_file

  @staticmethod
  def __read_file( filename ):
    """
    Read a file and return all of its contents.

    @type filename: unicode
    @param filename: full path of the file to read
    @rtype: unicode
    @return: full contents of the file
    """
    return file( filename ).read()

  def upgrade_schema( self, to_version ):
    """
    Upgrade the database from its current version to a given version, applying all intervening
    schema delta files necessary to get there, and apply them in version order. If the given
    version is unknown, this method will upgrade to the latest known schema version that is
    before the given version.

    @type to_version: unicode
    @param to_version: the desired version to upgrade to, as a string
    """
    to_version = self.version_string_to_tuple( to_version )
    from_version = self.schema_version( self.__database )
    self.__database.commit()

    # if the database schema version is already equal to to_version, there's nothing to do
    if to_version == from_version:
      return

    if self.__database.backend == Persistent.SQLITE_BACKEND:
      extension = u"sqlite"
    else:
      extension = u"sql"

    filenames = self.__glob( u"model/delta/*.%s" % extension )
    versions = []

    # make a list of all available schema delta files
    for filename in filenames:
      base_filename = os.path.basename( filename )

      try:
        version = self.version_string_to_tuple( base_filename )
      except ValueError:
        continue

      # skip those versions that won't help us upgrade
      if version <= from_version:
        continue
      if version > to_version:
        continue

      versions.append( ( version, filename ) )

    # sort the schema delta files by version
    versions.sort( lambda a, b: cmp( a[ 0 ], b[ 0 ] ) )

    # apply the schema delta files in sorted order
    for ( version, filename ) in versions:
      self.apply_schema_delta( version, filename )

    self.__database.commit()
    print "successfully upgraded database schema"

  @staticmethod
  def schema_version( database, default_version = None ):
    try:
      schema_version = database.select_one( tuple, "select * from schema_version;" );
    # if there's no schema version table, then use the default version given. if there's no default
    # version, then assume the from_version is 1.5.4, which was the last version not to include a
    # schema_version table
    except:
      database.rollback()
      schema_version = default_version or ( 1, 5, 4 )

      # "release" is a reserved keyword in newer versions of sqlite, so put it in quotes
      database.execute( "create table schema_version ( major numeric, minor numeric, \"release\" numeric );", commit = False );
      database.execute( "insert into schema_version values ( %s, %s, %s );" % schema_version, commit = False );

    return schema_version

  def apply_schema_delta( self, version, filename ):
    """
    Upgrade the database from its current version to a given version, applying only the named
    schema delta file to do so. The changes are commited once complete, and the schema_version
    within the database is updated accordingly. This method assumes that the schema_version
    table exists and has one row.

    @type version: tuple
    @param version: ( major, minor, release ) with each version part as an integer
    @type filename: unicode
    @param filename: full path to the schema delta file to apply
    """
    print "upgrading database schema to version %s.%s.%s" % version

    # note: SQLite will auto-commit before certain statements (such as "create table"), which sort
    # of defeats the point of transactions. doing an explicit "begin transaction" first gives an
    # error later
    # http://oss.itsystementwicklung.de/download/pysqlite/doc/sqlite3.html#sqlite3-controlling-transactions

    self.__database.execute_script( self.__read_file( filename ), commit = False )
    self.__database.execute( "update schema_version set major = %s, minor = %s, \"release\" = %s;" % version, commit = False );
    self.__database.commit()

  @staticmethod
  def version_string_to_tuple( version ):
    """
    Given a version string with an optional file extension tacked on, convert the version to a
    tuple of integers and return it.

    @type version: unicode
    @param version: a version string of the form "major.minor.release"
    @rtype: tuple
    @return: ( major, minor, release ) with each version part as an integer
    @raises ValueError: invalid version or version parts cannot be converted to integers
    """
    VERSION_PARTS_COUNT = 3

    parts = version.split( "." )
    length = len( parts )

    if length == VERSION_PARTS_COUNT + 1:
      ( major, minor, release, extension ) = parts
    elif length == VERSION_PARTS_COUNT:
      ( major, minor, release ) = parts
    else:
      raise ValueError()

    try:
      major = int( major )
      minor = int( minor )
      release = int( release )
    except ( TypeError, ValueError ):
      raise ValueError()

    return ( major, minor, release )
