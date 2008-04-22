from Rss_tags import Item, Title, Link, Description, Dc_date, Dc_creator, Guid


class Rss_item( Item ):
  def __init__( self, title, link, description, date, guid ):
    Item.__init__(
      self,
      Title( title ),
      Link( link ),
      Description( description ),
      Dc_date( date ),
      # if we don't set the separator to empty, Node inserts newlines when the guid gets too long.
      # newlines in guids make Thunderbird angry
      Guid( guid, separator = u"" ),
    )
