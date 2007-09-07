function Editor( id, notebook_id, note_text, deleted_from, revisions_list, read_write, startup, highlight, focus ) {
  this.id = id;
  this.notebook_id = notebook_id;
  this.initial_text = note_text;
  this.deleted_from = deleted_from || null;
  this.revisions_list = revisions_list || new Array();
  this.read_write = read_write;
  this.startup = startup || false; // whether this Editor is for a startup note
  this.init_highlight = highlight || false;
  this.init_focus = focus || false;
  this.closed = false;
  var iframe_id = "note_" + id;

  this.document = null;
  this.iframe = createDOM( "iframe", {
    "id": iframe_id,
    "name": iframe_id,
    "class": "note_frame"
  } );
  this.iframe.editor = this;
  this.title = null;

  this.delete_button = createDOM( "input" );
  this.changes_button = createDOM( "input" );
  this.undelete_button = createDOM( "input" );
  this.options_button = createDOM( "input" );
  this.hide_button = createDOM( "input" );

  connect( this.iframe, "onload", function ( event ) { self.finish_init(); } );
}

Editor.prototype.finish_init = function () {
  if ( this.iframe.contentDocument ) { // browsers such as Firefox
    this.document = this.iframe.contentDocument;
  } else { // browsers such as IE
    this.document = this.iframe.contentWindow.document;
  }

  if ( !this.initial_text )
    this.initial_text = "<h3>";

  this.document.write( this.initial_text );

  this.scrape_title();

  if ( this.init_focus )
    this.focus();

  this.calls = new Array();
}

Editor.prototype.add_call = function ( method_name, args ) {
  this.calls[ this.calls.length ] = [ method_name, args || [] ];
}

Editor.prototype.highlight = function ( scroll ) {
  this.add_call( "highlight", [ scroll ] );
}

Editor.prototype.exec_command = function ( command, parameter ) {
  this.add_call( "exec_command", [ command, parameter ] );
}

Editor.prototype.resize = function () {
  this.add_call( "resize" );
}

Editor.prototype.empty = function () {
  this.add_call( "empty" );

  if ( !this.document || !this.document.body )
    return true; // consider it empty as of now

  return ( scrapeText( this.document.body ).length == 0 );
}

Editor.prototype.start_link = function () {
  this.add_call( "start_link" );
}

Editor.prototype.end_link = function () {
  this.add_call( "end_link" );
}

Editor.prototype.find_link_at_cursor = function () {
  this.add_call( "find_link_at_cursor" );

  return null;
}

Editor.prototype.focus = function () {
  this.add_call( "focus" );
}

// return true if the specified state is enabled
Editor.prototype.state_enabled = function ( state_name ) {
  this.add_call( "state_enabled", [ state_name ] );

  return false;
}

Editor.prototype.contents = function () {
  this.add_call( "contents" );

  return this.document.body.innerHTML;
}

Editor.prototype.shutdown = function( event ) {
  this.add_call( "shutdown", [ event ] );
}

// convenience function for parsing a link that has an href URL containing a query string
function parse_query( link ) {
  if ( !link || !link.href )
    return new Array();

  return parseQueryString( link.href.split( "?" ).pop() );
}

// convenience function for getting a link's title (stripped of whitespace), either from a query
// argument in the href or from the actual link title
function link_title( link, query ) {
  if ( !query )
    query = parse_query( link );

  var link_title = strip( query.title || scrapeText( link ) );

  // work around an IE quirk in which link titles are sometimes 0xa0
  if ( link_title.charCodeAt( 0 ) == 160 )
    return "";

  return link_title;
}
