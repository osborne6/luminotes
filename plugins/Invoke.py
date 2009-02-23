import imp
import plugins

def invoke( plugin_type, plugin_name, *args, **kwargs ):
  plugin_name = u"%s_%s" % ( plugin_type, plugin_name )
  plugin_module = getattr( plugins, plugin_name )
  function = getattr( plugin_module, plugin_type )

  return apply( function, args, kwargs )
