from htmllib import HTMLParser
from formatter import AbstractFormatter, NullWriter


class Html_nuker( HTMLParser ):
  """
  Nukes HTML of all tags, and optionally all entity/characters references.
  """
  def __init__( self, allow_refs = False ):
    HTMLParser.__init__( self, AbstractFormatter( NullWriter() ) )
    self.result = []
    self.allow_refs = allow_refs

  def handle_data( self, data ):
    if data and "<" not in data and ">" not in data:
      self.result.append( data )
      
  def handle_charref( self, ref ):
    ref = int( ref )
    if self.allow_refs:
      self.result.append( "&#%s;" % ref )
    # convert ascii references to their character equivalents
    elif ref >= 32 and ref < 128:
      self.result.append( chr( ref ) )

  def handle_entityref( self, ref ):
    if self.allow_refs:
      self.result.append( "&%s;" % ref )
    else:
      self.result.append( {
        "amp": "&",
        "lt": "<",
        "gt": ">",
        "quot": '"',
      }.get ( ref ) )

  def handle_comment( self, comment ):
    pass

  def handle_starttag( self, tag, method, attrs ):
    pass
      
  def handle_endtag( self, tag, attrs ):
    pass
      
  def unknown_starttag( self, tag, attributes ):
    pass

  def unknown_endtag( self, tag ):
    pass

  def nuke( self, rawstring ):
    """
    Nukes the given string of all HTML tags.
    """
    if rawstring is None:
      return u""

    self.reset()
    self.result = []
    self.feed( rawstring )

    return u"".join( self.result )
