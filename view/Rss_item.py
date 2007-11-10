from Rss_tags import Item, Title, Link, Description, Dc_date, Dc_creator, Guid


class Rss_item( Item ):
  def __init__( self, title, link, description, date, guid ):
    Item.__init__(
      self,
      Title( title ),
      Link( link ),
      Description( description ),
      Dc_date( date ),
      Guid( guid ),
    )
