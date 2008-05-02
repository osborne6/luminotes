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
      bracketed = "</%s>" % tag
      self.result.append( bracketed )
      
  def unknown_starttag( self, tag, attr ):
    self.handle_starttag( tag, None, attr )

  def unknown_endtag( self, tag ):
    self.handle_endtag( tag, None )

  # used to replace, for instance, "<br/>" with "<br />"
  INVALID_TAG_PATTERN = re.compile( "(\S)/>" )
  INVALID_TAG_FIX = "\\1 />"
  START_TAG_PATTERN = re.compile( "<([^/][^>]*)>" )
  END_TAG_PATTERN = re.compile( "</([^>]+)>" )

  def diff( self, html_a, html_b ):
    """
    Return a composite HTML diff of the given HTML input strings.
    """
    # parse html_a into a list
    self.reset()
    self.result = []
    html_a = self.INVALID_TAG_PATTERN.sub( self.INVALID_TAG_FIX, html_a )
    self.feed( html_a )
    a = [ x for x in self.result if x != "" ]

    # parse html_b into a list
    self.reset()
    self.result = []
    html_b = self.INVALID_TAG_PATTERN.sub( self.INVALID_TAG_FIX, html_b )
    self.feed( html_b )
    b = [ x for x in self.result if x != "" ]

    ( a, b ) = self.__prepare_lists( a, b )
    return self.__diff_lists( a, b )

  @staticmethod
  def __track_open_tags( item, open_tags ):
    """
    Add or remove from the open_tags list based on whether the given item is a start or end
    tag.
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

  def __prepare_lists( self, a, b ):
    """
    Prepare the two lists for diffing by merging together adjacent elements within
    modified/inserted/deleted start and end HTML tags.
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
        Html_differ.__track_open_tags( a[ i ], open_tags )
      for j in range( j1, j2 ):
        Html_differ.__track_open_tags( b[ j ], open_tags )

      if change_type == "replace":
        open_del_items.extend( a[ i1:i2 ] )
        open_ins_items.extend( b[ j1:j2 ] )
      elif change_type == "delete":
        open_del_items.extend( a[ i1:i2 ] )
      elif change_type == "insert":
        open_ins_items.extend( b[ j1:j2 ] )

      if len( open_tags ) == 0:
        result_a.append( ''.join( open_del_items ) )
        result_b.append( ''.join( open_ins_items ) )
        open_del_items = []
        open_ins_items = []

    return ( result_a, result_b )

  def __diff_lists( self, a, b ):
    """
    Diff two prepared lists and return the result as an HTML string.
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
