function Invoker() {
  this.pending_count = 0;
}

// Invoke the given URL with a remote scripting call, providing the data args as an associative
// array of key/value pairs. Optionally, the name of a form to scrape for args can also be provided.
// http_type should be 'POST' or 'GET'.
Invoker.prototype.invoke = function ( url, http_type, args, callback, form, synchronous, fire_and_forget ) {
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

  if ( synchronous )
    fire_and_forget = true;

  if ( !fire_and_forget ) {
    if ( this.pending_count == 0 ) {
      var loading = createDOM( "span", { "class": "status_text" }, "loading" );
      replaceChildNodes( "status_area", loading );
    }
    this.pending_count += 1;
  }

  if ( http_type == 'POST' ) {
    // HTTP POST
    request = getXMLHttpRequest();
    request.open( http_type, url, synchronous != true );
    request.setRequestHeader( 'Content-Type', 'application/x-www-form-urlencoded' );
    if ( arg_names.length > 0 )
      var doc = sendXMLHttpRequest( request, queryString( arg_names, arg_values ) );
    else
      var doc = sendXMLHttpRequest( request );
  } else {
    // HTTP GET
    if ( arg_names.length > 0 )
      var doc = doSimpleXMLHttpRequest( url, arg_names, arg_values );
    else
      var doc = doSimpleXMLHttpRequest( url );
  }

  if ( fire_and_forget )
    return;

  var self = this;
  doc.addCallbacks(
    function ( request ) {
      self.handle_response( request, callback );
    }, 
    function () {
      self.pending_count -= 1;
      replaceChildNodes( "status_area", createDOM( "span" ) );
      signal( self, "error_message", "There was a problem reaching the server. Please check your network connectivity." );
    }
  );
}

Invoker.prototype.handle_response = function ( request, callback ) {
  // if there are no more pending requests, clear the loading status
  this.pending_count -= 1;
  if ( this.pending_count == 0 )
    replaceChildNodes( "status_area", createDOM( "span" ) );

  var result = evalJSONRequest( request );

  if ( result.error )
    signal( this, "error_message", result.error );

  if ( result.message )
    signal( this, "message", result.message );

  if ( callback )
    callback( result );

  if ( result.redirect )
    window.location = result.redirect;

  if ( result.reload )
    window.location.reload();
}
