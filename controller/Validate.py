import cherrypy
from cgi import escape
from Html_cleaner import Html_cleaner


class Validation_error( Exception ):
  """
  An exception raised when form validation fails for some reason.
  """

  MESSAGE_MAP = {
    int: u"can only contain digits",
  }

  def __init__( self, name, value, value_type, message = None ):
    Exception.__init__( self )
    self.__name = name
    self.__value = value
    self.__value_type = value_type

    if message is None:
      # if the value's type has a message member, use that. otherwise, look up the type in a map
      if hasattr( value_type, u"message" ):
        self.__message = value_type.message
      else:
        self.__message = self.MESSAGE_MAP.get( value_type, u"is invalid" )
    else:
      self.__message = message

  def __str__( self ):
    return self.__message

  def to_dict( self ):
    return dict(
      error = u"The %s %s." % ( self.__name, self.__message ),
      name = self.__name,
      value = self.__value,
    )

  name = property( lambda self: self.__name )
  value = property( lambda self: self.__value )
  value_type = property( lambda self: self.__value_type )
  message = property( lambda self: self.__message )


class Valid_string( object ):
  """
  Validator for a string of certain minimum and maximum lengths.
  """
  moron_map = {
    u"\xa0": u" ",
    u"\xa9": u"(c)",
    u"\xae": u"(r)",
    u"\xb7": u"*",
    u"\u2002": u" ",
    u"\u2003": u" ",
    u"\u2009": u" ",
    u"\u2010": u"-",
    u"\u2011": u"-",
    u"\u2013": u"-",
    u"\u2014": u"--",
    u"\u2015": u"--",
    u"\u2016": u"--",
    u"\u2017": u"||",
    u"\u2018": u"'",
    u"\u2019": u"'",
    u"\u201a": u",",
    u"\u201b": u"'",
    u"\u201c": u'"',
    u"\u201d": u'"',
    u"\u201e": u",,",
    u"\u201f": u'"',
    u"\u2022": u"*",
    u"\u2023": u"*",
    u"\u2024": u".",
    u"\u2025": u"..",
    u"\u2026": u"...",
    u"\u2027": u".",
    u"\u2122": u"(tm)",
  }

  def __init__( self, min = None, max = None, escape_html = True ):
    self.min = min
    self.max = max
    self.escape_html = escape_html
    self.message = None

  def __call__( self, value ):
    value = self.__demoronize( value.strip() )

    if self.min is not None and len( value ) < self.min:
      if self.min == 1:
        self.message = u"is missing"
      else:
        self.message = u"must be at least %s characters long" % self.min
      raise ValueError()
    elif self.max is not None and len( value ) > self.max:
      self.message = u"must be no longer than %s characters" % self.max
      raise ValueError()

    # either escape all html completely or just clean up the html, stripping out everything that's
    # not on a tag/attribute whitelist
    if self.escape_html:
      return escape( value, quote = True )
    else:
      cleaner = Html_cleaner()
      return cleaner.strip( value )

  def __demoronize( self, value ):
    """
    Convert stupid Microsoft unicode symbols to saner, cross-platform equivalents.
    """
    try:
      for ( moron_symbol, replacement ) in self.moron_map.items():
        value = value.replace( moron_symbol, replacement )
    except:
      import traceback
      traceback.print_exc()
      raise

    return value


class Valid_bool( object ):
  """
  Validator for a boolean value.
  """
  def __call__( self, value ):
    value = value.strip()

    if value in ( u"True", u"true" ): return True
    if value in ( u"False", u"false" ): return False

    raise ValueError()


def validate( **expected ):
  """
  validate() can be used to require that the arguments of the decorated method successfully pass
  through particular validators. The validate() method itself is evaluated where it is used as a
  decorator, which just returns decorate() to be used as the actual decorator.

  Example usage:

    @validate(
      foo = Valid_string( min = 5, max = 10 ),
      bar = int
    )
    def method( self, foo, bar ): pass

  Note that validate() currently only works for instance methods (methods that take self as the
  first argument). Also note that you can use multiple validators for a single argument.

  Example usage:

    @validate(
      foo = Valid_string( min = 5, max = 10 ),
      bar = ( int, valid_bar )
    )
    def method( self, foo, bar ): pass

  """
  def decorate( function ):
    """
    When the method being decorated is invoked, its decorator gets invoked instead and is supposed
    to return a new function to use in place of the method being decorated (or a modified version
    of that function). In this case, the decorator is our decorate() function, and the function it
    returns is the check() function. decorate()'s first argument is the method being decorated.
    """
    def check( *args, **kwargs ):
      """
      check() pretends that it's the method being decorated. It takes the same arguments and then
      invokes the actual method being decorated, passing in those arguments, but only after first
      validating all of those arguments to that function. If validation fails, a Validation_error
      is raised. Note that in Python, keyword argument names have to be str, not unicode.
      """
      args = list( args )
      args_index = 1 # skip the self argument

      # determine the expected argument names from the decorated function itself
      code = function.func_code
      expected_names = code.co_varnames[ : code.co_argcount ]

      # validate each of the expected arguments
      for expected_name in expected_names:
        if expected_name == u"self": continue
        expected_type = expected.get( expected_name )        

        # look for expected_name in kwargs and store the validated value there
        if expected_name in kwargs:
          value = kwargs.get( expected_name )
          # if there's a tuple of multiple validators for this expected_name, use all of them
          if isinstance( expected_type, tuple ):
            for validator in expected_type:
              try:
                value = validator( value )
              except ( ValueError, TypeError ):
                raise Validation_error( expected_name, value, validator )
            kwargs[ str( expected_name ) ] = value
          # otherwise, there's just a single validator
          else:
            try:
              kwargs[ str( expected_name ) ] = expected_type( value )
            except ( ValueError, TypeError ):
              raise Validation_error( expected_name, value, expected_type )
          continue

        # expected_name wasn't found in kwargs, so look for it in args. if it's not there either,
        # raise unless there's a default value for the argument in the decorated function
        if args_index >= len( args ):
          if function.func_defaults and args_index >= len( args ) - len( function.func_defaults ):
            continue
          raise Validation_error( expected_name, None, expected_type, message = u"is required" )
        value = args[ args_index ]

        # if there's a tuple of multiple validators for this expected_name, use all of them
        if isinstance( expected_type, tuple ):
          for validator in expected_type:
            try:
              value = validator( value )
            except ( ValueError, TypeError ):
              raise Validation_error( expected_name, value, validator )
          args[ args_index ] = value
        # otherwise, there's just a single validator
        else:
          try:
            args[ args_index ] = expected_type( value )
          except ( ValueError, TypeError ):
            raise Validation_error( expected_name, value, expected_type )
        args_index += 1

      # if there are any unexpected arguments, raise
      for ( arg_name, arg_value ) in kwargs.items():
        if not arg_name in expected_names:
          print arg_name, expected
          raise Validation_error( arg_name, arg_value, None, message = u"is an unknown argument" )

      return function( *args, **kwargs )

    return check

  return decorate
