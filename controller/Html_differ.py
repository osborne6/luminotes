import re
from difflib import SequenceMatcher
from htmllib import HTMLParser
from formatter import AbstractFormatter, NullWriter
from xml.sax.saxutils import quoteattr


class Html_differ( HTMLParser ):
  """
  Generates an HTML diff for two HTML strings. It assumed that the input HTML is already cleaned.
  """
  def __init__( self ):
    HTMLParser.__init__( self, AbstractFormatter( NullWriter() ) )
    self.result = []
    self.requires_no_close = [ 'img', 'br' ]

  WORD_AND_WHITESPACE_PATTERN = re.compile( "\S*\s*" )

  def handle_data( self, data ):
    # this turns "foo bar baz" into [ "foo ", "bar ", "baz" ] and extends the result with it
    self.result.extend( self.WORD_AND_WHITESPACE_PATTERN.findall( data ) )

  def handle_charref( self, ref ):
    self.result.append( '&#%s;' % ref )

  def handle_entityref( self, ref ):
    self.result.append( '&%s;' % ref )

  def handle_comment( self, comment ):
    pass # ignore comments

  def handle_starttag( self, tag, method, attrs ):
    self.result.append( self.get_starttag_text() )
      
  def handle_endtag( self, tag, attrs ):
    if tag not in self.requires_no_close:
      self.result.append( "</%s>" % tag )
      
  def unknown_starttag( self, tag, attr ):
    self.handle_starttag( tag, None, attr )

  def unknown_endtag( self, tag ):
    self.handle_endtag( tag, None )

  # used to replace, for instance, "<br/>" with "<br />"
  INVALID_TAG_PATTERN = re.compile( "(\S)/>" )
  INVALID_TAG_FIX = "\\1 />"

  def convert_html_to_list( self, html ):
    """
    Given an HTML string, produce a list of its constituent elements (tags and text).

    @type html: unicode
    @param html: HTML string to parse
    @rtype: [ unicode, ... ]
    @return: parsed list of HTML elements
    """
    self.reset()
    self.result = []
    html = self.INVALID_TAG_PATTERN.sub( self.INVALID_TAG_FIX, html )
    self.feed( html )
    return [ x for x in self.result if x != "" ]

  def diff( self, html_a, html_b ):
    """
    Return a composite HTML diff of the given HTML input strings. The returned string contains the
    entirety of the input strings, but with deleted/modified text from html_a wrapped in <del> tags,
    and inserted/modified text from html_b wrapped in <ins> tags.

    @type html_a: unicode
    @param html_a: original HTML string
    @type html_b: unicode
    @param html-b: modified HTML string
    @rtype: unicode
    @return: composite HTML diff
    """
    # parse the two html strings into lists
    a = self.convert_html_to_list( html_a )
    b = self.convert_html_to_list( html_b )

    # prepare the two lists for diffing, and then diff 'em
    ( a, b ) = self.prepare_lists( a, b )
    return self.diff_lists( a, b )

  START_TAG_PATTERN = re.compile( "<([^/][^>]*)>" )
  END_TAG_PATTERN = re.compile( "</([^>]+)>" )

  @staticmethod
  def track_open_tags( item, open_tags ):
    """
    Add or remove from the open_tags list based on whether the given item contains a start or end
    tag. If item does not contain any tag, then open_tags remains unchanged.

    @type item: unicode
    @param item: chunk of HTML, containing either an HTML tag or just text
    @type open_tags: [ unicode, ... ]
    @param open_tags: list of open tags
    """
    match = Html_differ.START_TAG_PATTERN.search( item )
    if match:
      open_tags.append( match.group( 1 ) )
      return

    match = Html_differ.END_TAG_PATTERN.search( item )
    if not match: return

    tag = match.group( 1 )
    if match and tag in open_tags:
      open_tags.remove( tag )

  def prepare_lists( self, a, b ):
    """
    Prepare the two lists for diffing by merging together adjacent elements that occur within
    modified start and end HTML tags.

    For instance, if:
      a = [ 'foo ', 'bar ', 'baz ', 'quux' ]
      b = [ 'foo ', '<i>', 'bar ', 'baz', '</i> ', 'quux' ]
    then the returned lists are as follows:
      a = [ 'foo ', 'bar baz ', 'quux' ]
      b = [ 'foo ', '<i>bar baz</i> ', 'quux' ]

    Merging these elements together ensures that they're diffed as a single unit. Failing to perform
    this step would mean that when a phrase in list a becomes italicized in list b, then it wouldn't
    show up as modified in the resulting diff.

    @type a: [ unicode, ... ]
    @type b: [ unicode, ... ]
    @rtype: ( [ unicode, ... ], [ unicode, ... ] )
    @return: tuple of resulting list a and list b
    """
    matcher = SequenceMatcher( None, a, b )
    result_a = []
    result_b = []
    open_tags = []      # modified start tags
    open_del_items = [] # deleted items within modified start and end tags
    open_ins_items = [] # inserted items within modified start and end tags

    for ( change_type, i1, i2, j1, j2 ) in matcher.get_opcodes():
      if change_type == "equal":
        equal_items = b[ j1:j2 ]
        if len( open_tags ) == 0:
          result_a.extend( equal_items )
          result_b.extend( equal_items )
        else:
          open_del_items.extend( equal_items )
          open_ins_items.extend( equal_items )
        continue

      # go through the altered items looking for start and end tags
      for i in range( i1, i2 ):
        Html_differ.track_open_tags( a[ i ], open_tags )
      for j in range( j1, j2 ):
        Html_differ.track_open_tags( b[ j ], open_tags )

      if change_type == "replace":
        open_del_items.extend( a[ i1:i2 ] )
        open_ins_items.extend( b[ j1:j2 ] )
      elif change_type == "delete":
        open_del_items.extend( a[ i1:i2 ] )
      elif change_type == "insert":
        open_ins_items.extend( b[ j1:j2 ] )

      if len( open_tags ) == 0:
        if len( open_del_items ) > 0:
          result_a.append( ''.join( open_del_items ) )
        if len( open_ins_items ) > 0:
          result_b.append( ''.join( open_ins_items ) )
        open_del_items = []
        open_ins_items = []

    return ( result_a, result_b )

  def diff_lists( self, a, b ):
    """
    Diff two prepared lists and return the result as an HTML string.

    @type a: [ unicode, ... ]
    @type b: [ unicode, ... ]
    @rtype: unicode
    @return: composite HTML diff
    """
    matcher = SequenceMatcher( None, a, b )
    result = []
    open_tags = []

    # inspired by http://www.aaronsw.com/2002/diff/
    for ( change_type, i1, i2, j1, j2 ) in matcher.get_opcodes():
      if change_type == "replace":
        result.append(
          '<del class="diff modified">' + ''.join( a[ i1:i2 ] ) + '</del>' + \
          '<ins class="diff modified">' + ''.join( b[ j1:j2 ] ) + '</ins>'
        )
      elif change_type == "delete":
        result.append( '<del class="diff">' + ''.join( a[ i1:i2 ] ) + '</del>' )
      elif change_type == "insert":
        result.append( '<ins class="diff">' + ''.join( b[ j1:j2 ] ) + '</ins>' )
      elif change_type == "equal":
        result.append( ''.join( b[ j1:j2 ] ) )

    return "".join( result )
