function Invoker( handler ) {
  this.handler = handler;
}

Invoker.prototype.invoke = function ( url, http_type, args, callback, form, fire_and_forget ) {
  if ( form ) {
    var form = formContents( getElement( form ) );
    var arg_names = form[ 0 ];
    var arg_values = form[ 1 ];
  } else {
    var arg_names = [];
    var arg_values = [];
  }

  extend( arg_names, keys( args ) );
  extend( arg_values, values( args ) );

  // if there's no handler, simulate an error reaching the server
  if ( !this.handler ) {
    signal( self, "error_message", "There was a problem reaching the server. Please check your network connectivity." );
    return;
  }

  var args = new Array();
  for ( var i in arg_names ) {
    var name = arg_names[ i ];
    var value = arg_values[ i ];

    args[ name ] = value;
  }

  // ask the stub handler for a fake response to the invocation request
  var result = this.handler( url, args );

  if ( fire_and_forget )
    return;

  if ( result.error )
    signal( this, "error_message", result.error );

  if ( callback )
    callback( result );

  if ( result.redirect )
    window.location = result.redirect;

  if ( result.reload )
    window.location.reload();
}
