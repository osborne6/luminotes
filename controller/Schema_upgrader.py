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

    try:
      from_version = self.__database.select_one( tuple, "select * from schema_version;" );
    except:
      from_version = None

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
      if from_version and version <= from_version:
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

  def apply_schema_delta( self, version, filename ):
    """
    Upgrade the database from its current version to a given version, applying only the named
    schema delta file to do so.

    @type version: tuple
    @param version: ( major, minor, release ) with each version part as an integer
    @type filename: unicode
    @param filename: full path to the schema delta file to apply
    """
    self.__database.execute_script( self.__read_file( filename ), commit = False )

    try:
      self.__database.execute( "update schema_version set major = %s, minor = %s, release = %s;" % version, commit = False );
    # if the table doesn't yet exist, create it
    except:
      self.__database.execute( "create table schema_version ( major numeric, minor numeric, release numeric );", commit = False );
      self.__database.execute( "insert into schema_version values ( %s, %s, %s );" % version, commit = False );

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
