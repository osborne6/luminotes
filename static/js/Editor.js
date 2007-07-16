entry_titles = {} // map from entry title to the open editor for that entry

function Editor( id, entry_text, insert_after_iframe_id, read_write, startup, highlight, focus ) {
  this.initial_text = entry_text;
  this.id = id;
  this.read_write = read_write;
  this.startup = startup || false; // whether this Editor is for a startup entry
  this.init_highlight = highlight || false;
  this.init_focus = focus || false;
  var iframe_id = "entry_" + id;

  var self = this;
  this.document = null;
  this.iframe = createDOM( "iframe", {
    "src": "/notebooks/blank_entry/" + id,
    "frameBorder": "0",
    "scrolling": "no",
    "id": iframe_id,
    "name": iframe_id,
    "class": "entry_frame"
  } );
  this.iframe.editor = this;
  this.title = null;

  if ( read_write ) {
    this.delete_button = createDOM( "input", {
      "type": "button",
      "class": "entry_button",
      "id": "delete_" + iframe_id,
      "value": "delete",
      "title": "delete entry [ctrl-d]"
    } );
    connect( this.delete_button, "onclick", function ( event ) { signal( self, "delete_clicked", event ); } );

    this.options_button = createDOM( "input", {
      "type": "button",
      "class": "entry_button",
      "id": "options_" + iframe_id,
      "value": "options",
      "title": "entry options"
    } );
    connect( this.options_button, "onclick", function ( event ) { signal( self, "options_clicked", event ); } );
  }

  if ( read_write || !startup ) {
    this.hide_button = createDOM( "input", {
      "type": "button",
      "class": "entry_button",
      "id": "hide_" + iframe_id,
      "value": "hide",
      "title": "hide entry [ctrl-h]"
    } );
    connect( this.hide_button, "onclick", function ( event ) { signal( self, "hide_clicked", event ); } );
  }

  this.entry_controls = createDOM( "span", { "class": "entry_controls" },
    this.delete_button ? this.delete_button : null,
    this.delete_button ? " " : null,
    this.options_button ? this.options_button : null,
    this.options_button ? " " : null,
    this.hide_button ? this.hide_button : null
  );

  // if an iframe has been given to insert this new editor after, then insert the new editor's
  // iframe. otherwise just append the iframe for the new editor
  if ( insert_after_iframe_id ) {
    insertSiblingNodesAfter( insert_after_iframe_id, this.entry_controls );
    insertSiblingNodesAfter( this.entry_controls, this.iframe );
  } else {
    appendChildNodes( "entries", this.entry_controls );
    appendChildNodes( "entries", this.iframe );
  }
}

// second stage of construction, invoked by the iframe's body onload handler. do not call directly.
// four-stage construction is only necessary because IE is such a piece of shit
function editor_loaded( id ) {
  var iframe = getElement( "entry_" + id );
  setTimeout( function () { iframe.editor.init_document(); }, 1 );
}

// third stage of construction, invoked by the editor_loaded() function. do not call directly
Editor.prototype.init_document = function () {
  var self = this; // necessary so that the member functions of this editor object are used

  if ( this.iframe.contentDocument ) { // browsers such as Firefox
    this.document = this.iframe.contentDocument;

    if ( this.read_write ) {
      this.document.designMode = "On";    
    }
    setTimeout( function () { self.finish_init(); }, 1 );
  } else { // browsers such as IE
    this.document = this.iframe.contentWindow.document;

    if ( this.read_write ) {
      this.document.designMode = "On";   
      // work-around for IE bug: reget the document after designMode is turned on
      this.document = this.iframe.contentWindow.document;
    }
    setTimeout( function () { self.finish_init(); }, 100 );
  }
}

// fourth and final stage of construction, invoked by init_document(). do not call directly
Editor.prototype.finish_init = function () {
  if ( !this.initial_text )
    this.initial_text = "<h3>";

  this.insert_html( this.initial_text );

  var self = this; // necessary so that the member functions of this editor object are used
  if ( this.read_write ) {
    connect( this.document, "onkeydown", function ( event ) { self.key_pressed( event ); } );
    connect( this.document, "onkeyup", function ( event ) { self.key_released( event ); } );
  }

  connect( this.document, "onclick", function ( event ) { self.mouse_clicked( event ); } );
  connect( this.document, "onblur", function ( event ) { self.blurred( event ); } );
  connect( this.document, "onfocus", function ( event ) { self.focused( event ); } );
  connect( this.document.body, "onblur", function ( event ) { self.blurred( event ); } );
  connect( this.document.body, "onfocus", function ( event ) { self.focused( event ); } );

  // special-case: connect any submit buttons within the contents of this entry
  var signup_button = withDocument( this.document, function () { return getElement( "signup_button" ); } );
  if ( signup_button ) {
    var signup_form = withDocument( this.document, function () { return getElement( "signup_form" ); } );
    connect( signup_button, "onclick", function ( event ) {
      signal( self, "submit_form", "/users/signup", signup_form ); event.stop();
    } );
  }

  var login_button = withDocument( this.document, function () { return getElement( "login_button" ); } );
  if ( login_button ) {
    var login_form = withDocument( this.document, function () { return getElement( "login_form" ); } );
    connect( login_button, "onclick", function ( event ) {
      signal( self, "submit_form", "/users/login", login_form ); event.stop();
    } );
  }

  if ( this.iframe.contentDocument ) { // browsers such as Firefox
    if ( this.read_write ) this.exec_command( "styleWithCSS", false );
    this.resize();
    if ( this.init_highlight ) self.highlight();
  } else { // browsers such as IE, which won't resize correctly if done too soon
    setTimeout( function () {
      self.resize();
      if ( self.init_highlight ) self.highlight();
    }, 50 );
  }

  this.scrape_title();
  if ( this.init_focus )
    this.focus();
  signal( this, "state_changed", this );
}

Editor.prototype.highlight = function ( scroll ) {
  if ( scroll == undefined )
    scroll = true;

  if ( /Opera/.test( navigator.userAgent ) ) { // MochiKit's Highlight is broken in Opera
    if ( scroll ) ScrollTo( this.iframe );
    pulsate( this.iframe, options = { "pulses": 1, "duration": 0.5 } );
  } else if ( this.iframe.contentDocument ) { // browsers such as Firefox
    if ( scroll ) ScrollTo( this.iframe );
    Highlight( this.iframe, options = { "queue": { "scope": "highlight", "limit": 1 } } );
  } else { // browsers such as IE
    if ( scroll ) ScrollTo( this.iframe );
    if ( this.document && this.document.body )
      Highlight( this.document.body, options = { "queue": { "scope": "highlight", "limit": 1 } } );
  }
}

Editor.prototype.exec_command = function ( command, parameter ) {
  command = command.toLowerCase();

  if ( command == "h3" ) {
    if ( this.state_enabled( "h3" ) )
      this.document.execCommand( "formatblock", false, "normal" );
    else
      this.document.execCommand( "formatblock", false, "<h3>" );
    return;
  }

  this.document.execCommand( command, false, parameter );
}

Editor.prototype.insert_html = function ( html ) {
  if ( html.length == 0 ) return;

  if ( !this.read_write ) {
    this.document.body.innerHTML = html;
    return;
  }

  try { // browsers supporting insertHTML command, such as Firefox
    this.document.execCommand( "insertHTML", false, html );

    // for some reason, appending an empty span improves formatting
    spans = getElementsByTagAndClassName( "span", null, parent = this.document );
    if ( spans.length == 0 ) {
      var span = this.document.createElement( "span" );
      this.document.body.appendChild( span );
    }
  } catch ( e ) { // browsers that don't support insertHTML, such as IE
    this.document.body.innerHTML = html;
  }
}

// resize the editor's frame to fit the dimensions of its content
Editor.prototype.resize = function () {
  var dimensions;
  // TODO: find a better way to determine which dimensions to use than just checking for contentDocument
  if ( this.iframe.contentDocument ) // Firefox
    dimensions = { "h": elementDimensions( this.document.documentElement ).h };
  else // IE
    dimensions = { "h": this.document.body.scrollHeight };

  setElementDimensions( this.iframe, dimensions );
}

Editor.prototype.key_pressed = function ( event ) {
  signal( this, "key_pressed", this, event );

  this.resize();
}

Editor.prototype.key_released = function ( event ) {
  this.resize();

  // if non-alphabetic (a-z), non-ctrl keys are released, issue a state changed event
  var code = event.key().code;
  if ( ( code >= 65 && code <= 90 ) || event.modifier().ctrl )
    return;

  signal( this, "state_changed", this );
}

Editor.prototype.mouse_clicked = function ( event ) {
  event.stop();
  signal( this, "state_changed", this );

  // search through the tree of elements containing the clicked target. if a link isn't found, bail
  var link = event.target()
  while ( link.nodeName != "A" ) {
    link = link.parentNode;
    if ( !link )
      return;
  }
  if ( !link.href )
    return;

  // in case the link is to ourself, first grab the most recent version of our title
  this.scrape_title();

  var id;
  var link_title = scrapeText( link );
  var editor = entry_titles[ link_title ];
  var href_leaf = link.href.split( "/" ).pop();
  // if the link's title corresponds to an open entry id, set that as the link's destination
  if ( editor ) {
    id = editor.id;
    link.href = "/entries/" + id;
  // if this is a new link, get a new entry id and set it for the link's destination
  } else if ( href_leaf == "new" ) {
    signal( this, "load_editor_by_title", link_title, this.iframe.id );
    return;
  // otherwise, use the id from link's current destination
  } else {
    // the last part of the current link's href is the entry id
    id = href_leaf;
  }

  // find the entry corresponding to the linked id, or create a new entry
  var iframe = getElement( "entry_" + id );
  if ( iframe ) {
    iframe.editor.highlight();
    return;
  }

  signal( this, "load_editor", link_title, this.iframe.id, id );
}

Editor.prototype.scrape_title = function () {
  // scrape the entry title out of the editor
  var heading = getFirstElementByTagAndClassName( "h3", null, this.document );
  if ( !heading ) return;
  var title = scrapeText( heading );

  // delete the previous title (if any) from the entry_titles map
  if ( this.title )
    delete entry_titles[ this.title ];

  // record the new title in entry_titles
  this.title = title;
  entry_titles[ this.title ] = this;
}

Editor.prototype.focused = function () {
  signal( this, "focused", this );
}

Editor.prototype.blurred = function () {
  this.scrape_title();
}

Editor.prototype.empty = function () {
  if ( !this.document.body )
    return false; // we don't know yet whether it's empty

  return ( scrapeText( this.document.body ).length == 0 );
}

Editor.prototype.start_link = function () {
  // get the current selection, which is the link title
  if ( this.iframe.contentWindow && this.iframe.contentWindow.getSelection ) { // browsers such as Firefox
    var selection = this.iframe.contentWindow.getSelection();

    // if no text is selected, then insert a link with a placeholder nbsp as the link title, and
    // then immediately remove the link title once the link is created
    if ( selection.toString().length == 0 ) {
      this.insert_html( "&nbsp;" );
      var range = selection.getRangeAt( 0 );
      var container = range.startContainer;
      range.setStart( container, range.startOffset - 1 );

      this.exec_command( "createLink", "/entries/new" );

      container.nodeValue = "";
      selection.collapse( container, 0 );
    // otherwise, just create a link with the selected text as the link title
    } else {
      this.exec_command( "createLink", "/entries/new" );
    }
  } else if ( this.document.selection ) { // browsers such as IE
    var range = this.document.selection.createRange();

    // if no text is selected, then insert a link with a placeholder space as the link title, and
    // then select it
    if ( range.text.length == 0 ) {
      range.text = " ";
      range.moveStart( "character", -1 );
      range.select();
    }

    this.exec_command( "createLink", "/entries/new" );
  }
}

Editor.prototype.end_link = function () {
  if ( this.iframe.contentWindow && this.iframe.contentWindow.getSelection ) { // browsers such as Firefox
    this.exec_command( "unlink" );
  } else if ( this.document.selection ) { // browsers such as IE
    // if some text is already selected, unlink it and bail
    var range = this.document.selection.createRange();
    if ( range.text.length > 0 ) {
      this.exec_command( "unlink" );
      return;
    }

    // since execCommand() with "unlink" removes the entire link instead of just ending it, fake it
    // by appending a temporary span, selecting it, and then immediately removing it
    var span = this.document.createElement( "span" );
    span.innerHTML = "&nbsp;";
    range.parentElement().parentNode.appendChild( span );
    range.moveToElementText( span );
    range.select();
    range.pasteHTML( "" );
  }
}

Editor.prototype.focus = function () {
  if ( /Opera/.test( navigator.userAgent ) )
    this.iframe.focus();
  else
    this.iframe.contentWindow.focus();
}

// return true if the specified state is enabled
Editor.prototype.state_enabled = function ( state_name ) {
  state_name = state_name.toLowerCase();
  var format_block = this.document.queryCommandValue( "formatblock" ).toLowerCase();
  var heading = ( format_block == "h3" || format_block == "heading 3" );

  if ( state_name == "h3" )
    return heading;

  if ( state_name == "bold" && heading )
    return false;

  // to determine if we're within a link, see whether the current selection is contained (directly
  // or indirectly) by an "A" node
  if ( state_name == "createlink" ) {
    var link;
    if ( window.getSelection ) { // browsers such as Firefox
      var selection = this.iframe.contentWindow.getSelection();
      var range = selection.getRangeAt( 0 );
      link = range.endContainer;
    } else if ( this.document.selection ) { // browsers such as IE
      var range = this.document.selection.createRange();
      link = range.parentElement();
    }

    while ( link.nodeName != "A" ) {
      link = link.parentNode;
      if ( !link )
        return false;
    }
    if ( !link.href )
      return false;

    return true;
  }

  return this.document.queryCommandState( state_name )
}

Editor.prototype.contents = function () {
  return this.document.body.innerHTML;
}

Editor.prototype.shutdown = function( event ) {
  if ( this.title )
    delete entry_titles[ this.title ];

  var iframe = this.iframe;
  var entry_controls = this.entry_controls;
  disconnectAll( this );
  disconnectAll( this.delete_button );
  disconnectAll( this.options_button );
  disconnectAll( this.hide_button );
  disconnectAll( iframe );
  disconnectAll( this.document.body );
  disconnectAll( this.document );
  blindUp( iframe, options = { "duration": 0.5, afterFinish: function () {
    try {
      removeElement( entry_controls );
      removeElement( iframe );
    } catch ( e ) { }
  } } );
}
