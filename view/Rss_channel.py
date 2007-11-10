from Rss_tags import Rss, Channel, Title, Link, Description, Language


class Rss_channel( Rss ):
  MAX_ITEMS = 20

  def __init__( self, title, link, description, rss_items, language = None ):
    Rss.__init__(
      self,
      Channel(
        Title( u"%s" % title ),
        Link( link ),
        Description( description ),
        Language( language or u"en-us" ),
        rss_items[ : self.MAX_ITEMS ],
      ),
      version = u"2.0",
      xmlns_dc = u"http://purl.org/dc/elements/1.1/",
    )
