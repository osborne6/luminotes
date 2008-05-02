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

    return self.__diff_lists( a, b )

  def __diff_lists( self, a, b ):
    matcher = SequenceMatcher( None, a, b )
    result = []

    # inspired by http://www.aaronsw.com/2002/diff/
    for ( tag, i1, i2, j1, j2 ) in matcher.get_opcodes():
      if tag == "replace":
        result.append(
          '<del class="diff modified">' + ''.join( a[ i1:i2 ] ) + '</del>' + \
          '<ins class="diff modified">' + ''.join( b[ j1:j2 ] ) + '</ins>'
        )
      elif tag == "delete":
        result.append( '<del class="diff">' + ''.join( a[ i1:i2 ] ) + '</del>' )
      elif tag == "insert":
        result.append( '<ins class="diff">' + ''.join( b[ j1:j2 ] ) + '</ins>' )
      elif tag == "equal":
        result.append( ''.join( b[ j1:j2 ] ) )

    return "".join( result )
