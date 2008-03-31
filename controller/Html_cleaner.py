# originally from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/496942

import urlparse
from htmllib import HTMLParser
from cgi import escape
from formatter import AbstractFormatter, NullWriter
from htmlentitydefs import entitydefs
from xml.sax.saxutils import quoteattr


def xssescape(text):
  """Gets rid of < and > and & and, for good measure"""
  return escape(text, quote=True)


class Html_cleaner(HTMLParser):
  """
  Cleans HTML of any tags not matching a whitelist.
  """
  def __init__( self ):
    HTMLParser.__init__( self, AbstractFormatter( NullWriter() ) )
    self.result = []
    self.open_tags = []
    # A list of the only tags allowed.  Be careful adding to this.  Adding
    # "script," for example, would not be smart.  'img' is out by default 
    # because of the danger of IMG embedded commands, and/or web bugs.
    self.permitted_tags = [
      'a',
      'b',
      'br',
      'em',
      'h3',
      'i',
      'li',
      'ol',
      'ul',
      'p',
      'strong',
      'u',
      'div',
      'h1',
      'h2',
      'h3',
      'h4',
      'h5',
      'h6',
      'blockquote',
      'q',
      'cite',
      'code',
      'samp',
      'kbd',
      'var',
      'dfn',
      'address',
      'big',
      'small',
      'ins',
      'del',
      'acronym',
      'abbr',
      'strike',
      's',
      'sub',
      'sup',
      'tt',
      'pre',
      'center',
      'font',
      'basefont',
      'multicol',
      'spacer',
      'layer',
      'ilayer',
      'nolayer',
      'img',
      'map',
      'area',
      'param',
      'hr',
      'nobr',
      'wbr',
      'ul',
      'ol',
      'li',
      'dl',
      'dt',
      'dd',
      'menu',
      'dir',
      'form',
      'input',
      'button',
      'label',
      'select',
      'option',
      'optgroup',
      'textarea',
      'fieldset',
      'legend',
      'table',
      'tr',
      'td',
      'th',
      'tbody',
      'tfoot',
      'thead',
      'caption',
      'col',
      'colgroup',
    ]

    # A list of tags that are forcibly removed from the input. Tags that
    # are not in permitted_tags and not in stripped_tags are simply
    # escaped.
    self.stripped_tags = [
      'span',
      'blink',
      'marquee',
      'bgsound',
      'meta',
      'object',
      'iframe',
      'script',
      'noscript',
      'applet',
      'embed',
      'style',
      'link',
      'html',
      'title',
      'head',
      'body',
    ]

    # A list of tags that require no closing tag.
    self.requires_no_close = [ 'img', 'br' ]

    # A dictionary showing the only attributes allowed for particular tags.
    # If a tag is not listed here, it is allowed no attributes.  Adding
    # "on" tags, like "onhover," would not be smart.  Also be very careful
    # of "background" and "style."
    self.allowed_attributes = {
      'a': [ 'href', 'target' ],
      'p': [ 'align' ],
      'img': [ 'alt', 'border', 'title' ],
      'table': [ 'cellpadding', 'cellspacing', 'border', 'width', 'height' ],
      'font': [ 'color', 'size', 'face' ],
      'td': [ 'rowspan', 'colspan', 'width', 'height' ],
      'th': [ 'rowspan', 'colspan', 'width', 'height' ],
    }

    # The only schemes allowed in URLs (for href and src attributes).
    # Adding "javascript" or "vbscript" to this list would not be smart.
    self.allowed_schemes = ['http','https','ftp', 'irc', '']

  def handle_data(self, data):
    if data:
      self.result.append( xssescape(data) )

  def handle_charref(self, ref):
    if len(ref) < 7 and ref.isdigit():
      self.result.append( '&#%s;' % ref )
    else:
      self.result.append( xssescape('&#%s' % ref) )

  def handle_entityref(self, ref):
    if ref in entitydefs:
      self.result.append( '&%s;' % ref )
    else:
      self.result.append( xssescape('&%s' % ref) )

  def handle_comment(self, comment):
    if comment:
      self.result.append( xssescape("<!--%s-->" % comment) )

  def handle_starttag(self, tag, method, attrs):
    if tag not in self.permitted_tags:
      if tag not in self.stripped_tags:
        self.result.append( xssescape("<%s>" %  tag) )
    else:
      bt = "<" + tag
      if tag in self.allowed_attributes:
        attrs = dict(attrs)
        self.allowed_attributes_here = \
          [x for x in self.allowed_attributes[tag] if x in attrs \
           and len(attrs[x]) > 0]
        for attribute in self.allowed_attributes_here:
          if attribute in ['href', 'src', 'background']:
            if self.url_is_acceptable(attrs[attribute]):
              bt += ' %s="%s"' % (attribute, attrs[attribute])
          else:
            bt += ' %s=%s' % \
               (xssescape(attribute), quoteattr(attrs[attribute]))
      if bt == "<a" or bt == "<img":
        return
      if tag in self.requires_no_close:
        bt += "/"
      bt += ">"           
      self.result.append( bt )
      self.open_tags.insert(0, tag)
      
  def handle_endtag(self, tag, attrs):
    bracketed = "</%s>" % tag
    if tag not in self.permitted_tags:
      if tag not in self.stripped_tags:
        self.result.append( xssescape(bracketed) )
    elif tag in self.open_tags:
      self.result.append( bracketed )
      self.open_tags.remove(tag)
      
  def unknown_starttag(self, tag, attributes):
    self.handle_starttag(tag, None, attributes)

  def unknown_endtag(self, tag):
    self.handle_endtag(tag, None)

  def url_is_acceptable(self,url):
    parsed = urlparse.urlparse(url)

    # Work-around a nasty bug. urlparse() caches parsed results and returns them on future calls,
    # and if the cache isn't cleared here, then a unicode string gets added to the cache, which
    # freaks out cherrypy when it independently calls urlparse() with the same URL later.
    urlparse.clear_cache()

    return parsed[0] in self.allowed_schemes

  def strip(self, rawstring):
    """Returns the argument stripped of potentially harmful HTML or JavaScript code"""
    self.reset()
    self.result = []
    self.feed(rawstring)
    for endtag in self.open_tags:
      if endtag not in self.requires_no_close:
        self.result.append( "</%s>" % endtag )
    return "".join( self.result )

  def xtags(self):
    """Returns a printable string informing the user which tags are allowed"""
    self.permitted_tags.sort()
    tg = ""
    for x in self.permitted_tags:
      tg += "<" + x
      if x in self.allowed_attributes:
        for y in self.allowed_attributes[x]:
          tg += ' %s=""' % y
      tg += "> "
    return xssescape(tg.strip())
