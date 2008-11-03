from Tags import P, Span, A, Strong

class Page_navigation( P ):
  def __init__( self, page_path, displayed_item_count, total_item_count, start, items_per_page, return_text = None ):
    if start is None or items_per_page is None:
      P.__init__( self )
      return

    if displayed_item_count == 1 and displayed_item_count < total_item_count:
      if not return_text:
        P.__init__( self )
        return

      P.__init__(
        self,
        Span(
          A(
            return_text,
            href = "%s" % page_path,
          ),
        ),
      )
      return

    if start == 0 and items_per_page >= total_item_count:
      P.__init__( self )
      return

    P.__init__(
      self,
      ( start > 0 ) and Span(
        A(
          u"previous",
          href = self.href( page_path, max( start - items_per_page, 0 ), items_per_page ),
        ),
        u" | ",
      ) or None,
      [ Span(
        ( start == page_start ) and Strong( unicode( page_number + 1 ) ) or A(
          Strong( unicode( page_number + 1 ) ),
          href = self.href( page_path, page_start, items_per_page ),
        ),
      ) for ( page_number, page_start ) in enumerate( range( 0, total_item_count, items_per_page ) ) ],
      ( start + items_per_page < total_item_count ) and Span(
        u" | ",
        A(
          u"next",
          href = self.href( page_path, min( start + items_per_page, total_item_count - 1 ), items_per_page ),
        ),
      ) or None,
    )

  @staticmethod
  def href( page_path, start, count ):
    # if start is zero, leave off start and count parameters and just use the defaults
    if start == 0:
      return page_path

    return u"%s?start=%d&count=%d" % ( page_path, start, count )
