class Node( object ):
  """
  An HTML node, consisting of an opening and closing HTML tag, potentially with stuff in between
  and attributes on the opening tag.
  """

  tag = None   # the name of the HTML tag to use for this node

  def __init__( self, *children, **attrs ):
    self.__attrs = attrs
    self.__children = []

    if "separator" in attrs:
      self.__separator = attrs[ "separator" ] 
      del( attrs[ "separator" ] )
    else:
      self.__separator = u"\n"

    if "prefix" in attrs:
      self.__prefix = attrs[ "prefix" ] 
      del( attrs[ "prefix" ] )
    else:
      self.__prefix = u""

    # flatten any lists contained within the children list.
    # so [ [ a, b ], [ c, d ] ] becomes just [ a, b, c, d ]
    for child in children:
      if child is None: continue

      if type( child ) == list:
        self.__children.extend( child )
      else:
        self.__children.append( child )

  children = property( lambda self: self.__children )
  attrs = property( lambda self: self.__attrs )

  def __str__( self ):
    # render this node's children
    rendered_children = self.__separator.join( [ unicode( child ) for child in self.__children ] )

    # if there is no tag, just return the children by themself
    if self.tag is None:
      return self.__prefix + rendered_children

    # render attributes in the open tag
    if len( self.__attrs ) == 0:
      open_tag = u"<%s>" % self.tag
    else:
      rendered_attrs = u" ".join( [ '%s="%s"' % ( Node.transform_name( name ), value )
                                   for ( name, value ) in self.__attrs.items() if value is not None ] )
      open_tag = u"<%s %s>" % ( self.tag, rendered_attrs )

    close_tag = u"</%s>" % self.tag

    # return the rendered node
    if len( self.__children ) == 0:
      return self.__prefix + u"%s%s" % ( open_tag, close_tag )
    elif len( self.__children ) == 1 and len( rendered_children ) < 80:
      separator = u""
    else:
      separator = self.__separator

    return self.__prefix + separator.join( [ open_tag, rendered_children, close_tag ] )

  @staticmethod
  def transform_name( name ):
    # since u"class" is a Python keyword, allow u"class_" instead
    if name == u"class_":
      return u"class"

    if name.endswith( u"_dc" ):
      # since Python identifiers can't contain colons, replace underscores with colons
      return name.replace( u"_", u":" )
    else:
      # since Python identifiers can't contain dashes, replace underscores with dashes
      return name.replace( u"_", u"-" )
