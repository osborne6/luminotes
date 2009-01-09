GECKO = /Gecko/.test( navigator.userAgent ) && !/like Gecko/.test( navigator.userAgent );
WEBKIT = /WebKit/.test( navigator.userAgent );
IE6 = /MSIE 6\.0/.test( navigator.userAgent );


function Editor( id, notebook_id, note_text, deleted_from_id, revision, read_write, startup, highlight, focus, position_after, start_dirty, own_notes_only ) {
  this.id = id;
  this.notebook_id = notebook_id;
  this.initial_text = note_text;
  this.start_dirty = start_dirty;
  this.deleted_from_id = deleted_from_id || null;
  this.revision = revision;
  this.user_revisions = new Array(); // cache for this note's list of revisions, loaded from the server on-demand
  this.read_write = read_write;      // whether the user has read-write access to this Editor
  this.own_notes_only = own_notes_only; // whether the user only has read-write access to their own notes
  this.edit_enabled = read_write && !deleted_from_id; // whether editing is actually enabled for this Editor
  this.startup = startup || false;   // whether this Editor is for a startup note
  this.init_highlight = highlight || false;
  this.init_focus = focus || false;
  this.closed = false;
  this.link_started = null;
  this.hover_target = null;
  this.hover_timer = null;
  this.document = null;
  this.iframe = null;
  this.div = null;
  this.title = "";

  // if the Editor is to be focused, create an editable iframe. otherwise just create a static div
  if ( highlight || focus )
    this.create_iframe( position_after );
  else
    this.create_div( position_after );
}

Editor.prototype.create_note_controls = function () {
  var iframe_id = "note_" + this.id;
  if ( this.read_write ) {
    this.delete_button = createDOM( "input", {
      "type": "button",
      "class": "note_button",
      "id": "delete_" + iframe_id,
      "value": "delete" + ( this.deleted_from_id ? " forever" : "" ),
      "title": "delete note [ctrl-d]"
    } );

    if ( this.deleted_from_id ) {
      this.undelete_button = createDOM( "input", {
        "type": "button",
        "class": "note_button",
        "id": "undelete_" + iframe_id,
        "value": "undelete",
        "title": "undelete note"
      } );
    } else if ( !this.own_notes_only ) {
      this.changes_button = createDOM( "input", {
        "type": "button",
        "class": "note_button",
        "id": "changes_" + iframe_id,
        "value": "changes",
        "title": "previous revisions"
      } );

      this.options_button = createDOM( "input", {
        "type": "button",
        "class": "note_button",
        "id": "options_" + iframe_id,
        "value": "options",
        "title": "note options"
      } );
    }
  }

  if ( !this.deleted_from_id && ( this.read_write || !this.startup ) && !this.own_notes_only ) {
    this.hide_button = createDOM( "input", {
      "type": "button",
      "class": "note_button",
      "id": "hide_" + iframe_id,
      "value": "hide",
      "title": "hide note [ctrl-h]"
    } );
  }

  this.note_controls = createDOM(
    "div", { "class": "note_controls", "id": "note_controls_" + this.id },
    this.delete_button ? this.delete_button : null,
    this.delete_button ? " " : null,
    this.changes_button ? this.changes_button : null,
    this.changes_button ? " " : null,
    this.options_button ? this.options_button : null,
    this.options_button ? " " : null,
    this.undelete_button ? this.undelete_button : null,
    this.undelete_button ? " " : null,
    this.hide_button ? this.hide_button : null
  );
}

Editor.prototype.connect_note_controls = function ( store_control_buttons ) {
  if ( store_control_buttons ) {
    var iframe_id = "note_" + this.id;
    this.delete_button = getElement( "delete_" + iframe_id );
    this.undelete_button = getElement( "undelete_" + iframe_id );
    this.changes_button = getElement( "changes_" + iframe_id );
    this.options_button = getElement( "options_" + iframe_id );
    this.hide_button = getElement( "hide_" + iframe_id );
  }

  var self = this;
  if ( this.delete_button )
    connect( this.delete_button, "onclick", function ( event ) { signal( self, "delete_clicked", event ); } );
  if ( this.undelete_button )
    connect( this.undelete_button, "onclick", function ( event ) { signal( self, "undelete_clicked", event ); } );
  if ( this.changes_button )
    connect( this.changes_button, "onclick", function ( event ) { signal( self, "changes_clicked", event ); } );
  if ( this.options_button )
    connect( this.options_button, "onclick", function ( event ) { signal( self, "options_clicked", event ); } );
  if ( this.hide_button )
    connect( this.hide_button, "onclick", function ( event ) { signal( self, "hide_clicked", event ); } );
}

Editor.prototype.create_iframe = function ( position_after ) {
  var iframe_id = "note_" + this.id;

  // if there is already an iframe for this Editor, bail
  var iframe = getElement( iframe_id );
  if ( iframe )
    return;

  var self = this;
  this.iframe = createDOM( "iframe",
    {
      // iframe src attribute is necessary in IE 6 on an HTTPS site to prevent annoying warnings
      "src": "about:blank",
      "frameBorder": "0",
      "scrolling": "no",
      "id": iframe_id,
      "name": iframe_id,
      "class": "note_frame invisible",
      "onresize": function () { setTimeout( function () { self.resize() }, 50 ); },
    }
  );
  this.iframe.editor = this;

  // if there is already a static note open for this editor, replace its div with the new iframe
  var static_note = getElement( "static_note_" + this.id );
  if ( static_note ) {
    this.note_controls = getElement( "note_controls_" + this.id );
    this.connect_note_controls( true );

    disconnectAll( this.div );
    addElementClass( static_note, "focused_note_frame" );

    var frame_height = elementDimensions( static_note ).h;
    insertSiblingNodesAfter( static_note, this.iframe );

    // give the invisible iframe the exact same position as the div it will replace
    setStyle( this.iframe, { "position": "fixed" } );
    setElementPosition( this.iframe, getElementPosition( static_note ) );

    // give the iframe the note's current contents and then resize it based on the size of the div
    this.set_iframe_contents( this.contents() );
    this.resize( frame_height );

    // make the completed iframe visible, and now remove the static div
    removeElementClass( this.iframe, "invisible" );
    removeElement( static_note );

    // set the iframe positioning back to standard static positioning and move the note controls
    setStyle( this.iframe, { "position": "static" } );
    insertSiblingNodesBefore( this.iframe, this.note_controls );

    // finally, turn on design mode so the iframe is editable
    this.enable_design_mode();

    this.div = null;
  } else {
    // TODO: rewrite this portion of the function as above
    this.create_note_controls();
    this.connect_note_controls();

    var note_holder = createDOM( "div", { "id": "note_holder_" + this.id },
      this.note_controls,
      this.iframe
    );

    if ( position_after && position_after.parentNode )
      insertSiblingNodesAfter( position_after, note_holder );
    else
      appendChildNodes( "notes", note_holder );

    this.set_iframe_contents( this.contents() );
    this.enable_design_mode();
  }

  this.finish_init();
}

Editor.prototype.set_iframe_contents = function ( contents_text ) {
  if ( this.iframe.contentDocument ) { // browsers such as Firefox
    this.document = this.iframe.contentDocument;
  } else { // browsers such as IE
    this.document = this.iframe.contentWindow.document;
  }

  this.document.open();
  if ( !contents_text ) {
    // hack: add a zero-width space to make the horizontal line under title show up in the
    // correct position, even before there is a title
    contents_text = "<h3>&#8203;";
  }

  this.document.write(
    '<html><head><style>html { padding: 1em; } body { font-size: 90%; line-height: 140%; font-family: sans-serif; } h3 { padding-bottom: 0.25em; border-bottom: 1px solid #dddddd; margin-bottom: 0.75em; } a[target ^= "_new"] { background: url(/static/images/web_icon_tiny.png) right center no-repeat; padding-right: 13px; } .diff a[target ^= "_new"] { background-image: none; padding-right: 0; } a:hover { color: #ff6600; } ins { color: green; text-decoration: none; } ins a { color: green; } del { color: red; text-decoration: line-through; } del a { color: red; } img { border-width: 0; } .left_justified { float: left; margin: 0.5em 1.5em 0.5em 0; } .center_justified { display: block; margin: 0.5em auto 0.5em auto; text-align: center; } .right_justified { float: right; margin: 0.5em 0 0.5em 1.5em; } hr { border: 0; color: #000000; background-color: #000000; height: 1px; } .button { border-style: outset; border-width: 0px; background-color: #d0e0f0; font-size: 100%; outline: none; cursor: pointer; } .button:hover { background-color: #ffcc66; } .revoke_button { margin-left: 0.5em; font-size: 90%; } .admin_button { margin-left: 0.5em; font-size: 90%; } .remove_user_button { margin-left: 0.5em; font-size: 90%; } .text_field { margin-top: 0.25em; padding: 0.25em; border: #999999 1px solid; } .textarea_field { margin-top: 0.25em; padding: 0.25em; border: #999999 1px solid; overflow: auto; } ul { list-style-type: disc; } ul li { margin-top: 0.5em; } ol li { margin-top: 0.5em; } .center_text { text-align: center; } .small_text { padding-top: 0.5em; font-size: 90%; } .radio_label { color: #000000; } .radio_label:hover { color: #ff6600; cursor: pointer; } .indented { margin-left: 1em; } .radio_table td { padding-right: 1em; } #import_notebook_table { font-size: 72%; border-collapse: collapse; border: 1px solid #999999; } #import_notebook_table td { border: 1px solid #999999; padding: 0.5em; } #import_notebook_table .heading_row { font-weight: bold; } .thumbnail_left { float: left; margin: 0.5em; margin-right: 1em; margin-bottom: 0.5em; border: 1px solid #999999; } .thumbnail_right { float: right; margin: 0.5em; margin-left: 1em; margin-bottom: 0.5em; border: 1px solid #999999; } .search_results_summary { font-size: 82%; } .invite_status { font-size: 82%; } .invite_link_area { font-size: 82%; margin-left: 2em; } .user_status { font-size: 82%; }</style>' +
    '<meta content="text/html; charset=UTF-8" http-equiv="content-type"></meta></head><body>' + contents_text + '</body></html>'
  );
  this.document.close();
}

Editor.prototype.enable_design_mode = function () {
  if ( this.iframe.contentDocument ) { // browsers such as Firefox
    if ( this.edit_enabled )
      this.document.designMode = "On";    
  } else { // browsers such as IE
    if ( this.edit_enabled ) {
      this.document.designMode = "On";   
      // work-around for IE bug: reget the document after designMode is turned on
      this.document = this.iframe.contentWindow.document;
    }
  }

  // move the text cursor to the end of the text
  if ( this.iframe.contentWindow && this.iframe.contentWindow.getSelection ) { // browsers such as Firefox
    var selection = this.iframe.contentWindow.getSelection();
    var last_node = this.document.body.lastChild;
    if ( last_node.nodeValue == "\n" && last_node.previousSibling )
      last_node = last_node.previousSibling;

    selection.selectAllChildren( last_node );
    selection.collapseToEnd();
  } else if ( this.document.selection ) { // browsers such as IE
    // TODO: finish this for IE
    var range = this.document.selection.createRange();
  }
}

Editor.prototype.create_div = function ( position_after ) {
  var self = this;

  // if there is already a static note div for this Editor, connect up the note controls and bail
  var static_note_div = getElement( "static_note_" + this.id );
  if ( static_note_div ) {
    this.note_controls = getElement( "note_controls_" + this.id );
    this.connect_note_controls( true );
    this.div = static_note_div;
    this.scrape_title();
    connect( this.div, "onclick", function ( event ) { self.focused( event ); } );
    return;
  }

  var static_contents = createDOM( "span", { "class": "static_note_contents" } );
  static_contents.innerHTML = this.contents();
  this.div = createDOM(
    "div", { "class": "static_note_div", "id": "static_note_" + this.id }, static_contents
  );

  // if there is already an iframe open for this editor, replace it with the new static note div
  if ( getElement( "note_" + this.id ) ) {
    disconnectAll( this.iframe.contentWindow );
    disconnectAll( this.document.body );
    disconnectAll( this.document );

    swapDOM( this.iframe, this.div );
    insertSiblingNodesBefore( this.div, this.note_controls );

    this.iframe = null;
    this.document = null;
  } else {
    this.create_note_controls();
    this.connect_note_controls();

    var note_holder = createDOM( "div", { "id": "note_holder_" + this.id },
      this.note_controls,
      this.div
    );

    if ( position_after && position_after.parentNode )
      insertSiblingNodesAfter( position_after, note_holder );
    else
      appendChildNodes( "notes", note_holder );
  }

  this.scrape_title();
  connect( this.div, "onclick", function ( event ) { self.focused( event ); } );

  signal( self, "init_complete" );
}

Editor.prototype.finish_init = function () {
  // since the browser may subtly tweak the html when it's inserted, save off the browser's version
  // of the html here. this yields more accurate comparisons within the dirty() method
  if ( this.start_dirty )
    this.initial_text = "";
  else
    this.initial_text = this.document.body.innerHTML;

  var self = this; // necessary so that the member functions of this editor object are used
  if ( this.edit_enabled ) {
    connect( this.document, "onkeydown", function ( event ) { self.key_pressed( event ); } );
    connect( this.document, "onkeyup", function ( event ) { self.key_released( event ); } );
  }
  connect( this.document, "onfocus", function ( event ) { self.focused( event ); } );
  connect( this.document.body, "onfocus", function ( event ) { self.focused( event ); } );
  connect( this.iframe.contentWindow, "onfocus", function ( event ) { self.focused( event ); } );
  connect( this.document, "onclick", function ( event ) { self.mouse_clicked( event ); } );
  connect( this.document, "onmouseover", function ( event ) { self.mouse_hovered( event ); } );
  connect( this.document, "ondragover", function ( event ) { self.mouse_dragged( event ); } );
  connect( this.iframe.contentWindow, "onpaste", function ( event ) { setTimeout( function () { self.resize() }, 50 ); } );
  connect( this.iframe.contentWindow, "oncut", function ( event ) { setTimeout( function () { self.resize() }, 50 ); } );

  // handle each form submit event by forwarding it on as a custom event
  function connect_form( form ) {
    connect( form, "onsubmit", function ( event ) {
      signal( self, "submit_form", form );
      event.stop();
    } );
  }

  var forms = getElementsByTagAndClassName( "form", null, this.document );
  for ( var i in forms ) {
    var form = forms[ i ];
    connect_form( form );
  }

  // connect each (non-submit) button to issue an event
  function connect_button( button ) {
    connect( button, "onclick", function ( event ) {
      signal( self, "button_clicked", this, button );
      event.stop();
    } );
  }

  var buttons = getElementsByTagAndClassName( "input", "button", this.document );
  for ( var i in buttons ) {
    var button = buttons[ i ];
    if ( button.getAttribute( "type" ) == "submit")
      continue;

    connect_button( button );
  }

  // browsers such as Firefox, but not Opera
  if ( this.iframe.contentDocument && !/Opera/.test( navigator.userAgent ) && this.edit_enabled ) {
    this.exec_command( "styleWithCSS", false );
    this.exec_command( "insertbronreturn", true );
  }

  if ( this.init_highlight ) self.highlight();

  this.scrape_title();
  if ( this.init_focus ) {
    this.focus();

    // special-case: focus any username field
    var username = withDocument( this.document, function () { return getElement( "username" ); } );
    if ( username )
      username.focus();
  }

  signal( self, "init_complete" );
}

Editor.prototype.highlight = function ( scroll ) {
  if ( scroll == undefined )
    scroll = true;

  var self = this;

  function do_highlight() {
    if ( self.div ) {
      new Highlight( self.div, options = { "queue": { "scope": "highlight", "limit": 1 } } );
      return;
    }

    if ( /Opera/.test( navigator.userAgent ) ) { // MochiKit's Highlight for iframes is broken in Opera
      pulsate( self.iframe, options = { "pulses": 1, "duration": 0.5 } );
    } else if ( self.iframe.contentDocument ) { // browsers such as Firefox
      new Highlight( self.iframe, options = { "queue": { "scope": "highlight", "limit": 1 } } );
    } else { // browsers such as IE
      if ( self.document && self.document.body )
        new Highlight( self.document.body, options = { "queue": { "scope": "highlight", "limit": 1 } } );
    }
  }

  // focusing the highlighted editor before scrolling to it prevents IE from deciding to
  // automatically scroll back to the link immediately afterwards
  this.focus();

  if ( scroll ) {
    var editor_node = this.iframe || this.div;

    // if the editor is already completely on-screen, then there's no need to scroll
    var viewport_position = getViewportPosition();
    if ( getElementPosition( this.note_controls ).y < viewport_position.y ||
         getElementPosition( editor_node ).y + getElementDimensions( editor_node ).h > viewport_position.y + getViewportDimensions().h ) {
      new ScrollTo( this.note_controls, { "afterFinish": do_highlight, "duration": 0.25 } );
      return;
    }
  }

  do_highlight();
}

Editor.prototype.exec_command = function ( command, parameter ) {
  command = command.toLowerCase();

  if ( command == "h3" ) {
    if ( this.state_enabled( "h3" ) )
      this.document.execCommand( "formatblock", false, "<p>" );
    else
      this.document.execCommand( "formatblock", false, "<h3>" );
    return;
  }

  this.document.execCommand( command, false, parameter );
}

Editor.prototype.insert_html = function ( html ) {
  if ( html.length == 0 ) return;

  if ( !this.edit_enabled || strip( this.contents() ) == "" ) {
    this.document.body.innerHTML = html;
    return;
  }

  try { // browsers supporting insertHTML command, such as Firefox
    this.document.execCommand( "insertHTML", false, html );
  } catch ( e ) { // browsers that don't support insertHTML, such as IE
    this.document.body.innerHTML = html;
  }
}

Editor.prototype.query_command_value = function ( command ) {
  return this.document.queryCommandValue( command );
}

// resize the editor's frame to fit the dimensions of its content
Editor.prototype.resize = function ( height ) {
  if ( !this.document ) return;
  var FRAME_BORDER_HEIGHT = 4; // 2 pixels at the top and 2 at the bottom

  if ( height ) {
    height -= FRAME_BORDER_HEIGHT;
  // if no height is given, get the height from this editor's document body
  } else {
    if ( WEBKIT ) {
      var self = this;
      withDocument( this.document, function () {
        var body = getFirstElementByTagAndClassName( "body" );
        height = elementDimensions( body ).h;
      } );
    } else if ( this.iframe.contentDocument ) { // Gecko and other sane browsers
      height = elementDimensions( this.document.documentElement ).h;
    } else { // IE
      height = this.document.body.scrollHeight;
    }
  }

  setElementDimensions( this.iframe, { "h": height } );
}

Editor.prototype.key_pressed = function ( event ) {
  signal( this, "key_pressed", this, event );

  this.resize();
}

Editor.prototype.key_released = function ( event ) {
  this.resize();

  // if ctrl keys are released, bail
  var code = event.key().code;
  var CTRL = 17;
  if ( event.modifier().ctrl || code == CTRL )
    return;

  this.cleanup_html( code );

  signal( this, "state_changed", this, false );
}

Editor.prototype.cleanup_html = function ( key_code ) {
  if ( WEBKIT ) {
    // if enter is pressed while in a title, end title mode, since WebKit doesn't do that for us
    var ENTER = 13; BACKSPACE = 8;
    if ( key_code == ENTER && this.state_enabled( "h3" ) )
      this.exec_command( "h3" );

    // if backspace is pressed, skip WebKit style scrubbing since it can cause problems
    if ( key_code == BACKSPACE )
      return null;

    // as of this writing, WebKit doesn't support execCommand( "styleWithCSS" ). for more info, see
    // https://bugs.webkit.org/show_bug.cgi?id=13490
    // so to make up for this shortcoming, manually scrub WebKit style spans and other nodes,
    // replacing them with appropriate tags
    var style_spans = getElementsByTagAndClassName( "span", null, this.document );
    var underlines = getElementsByTagAndClassName( "u", null, this.document );
    var strikethroughs = getElementsByTagAndClassName( "strike", null, this.document );
    var fonts = getElementsByTagAndClassName( "font", "Apple-style-span", this.document );
    var nodes = style_spans.concat( underlines ).concat( strikethroughs ).concat( fonts );

    for ( var i in nodes ) {
      var node = nodes[ i ];
      if ( !node ) continue;

      var style = node.getAttribute( "style" );

      node.removeAttribute( "class" );
      if ( style == undefined && node.tagName != "font" && node.tagName != "FONT" )
        continue;

      var replacement = withDocument( this.document, function () {
        // font-size is set when ending title mode
        if ( style.indexOf( "font-size: " ) != -1 )
          return null;
        if ( style.indexOf( "text-decoration: none;" ) != -1 || style.length == 0 )
          return createDOM( "span" );
        if ( style.indexOf( "font-weight: bold;" ) != -1 )
          return createDOM( "b" );
        if ( style.indexOf( "font-style: italic;" ) != -1 )
          return createDOM( "i" );
        if ( style.indexOf( "text-decoration: underline;" ) != -1 )
          return createDOM( "u" );
        if ( style.indexOf( "text-decoration: line-through;" ) != -1 )
          return createDOM( "strike" );
        return null;
      } );

      if ( replacement ) {
        var selection = this.iframe.contentWindow.getSelection();
        var anchor = selection.anchorNode;
        var offset = selection.anchorOffset;
        swapDOM( node, replacement );
        appendChildNodes( replacement, node.childNodes );

        // necessary to prevent the text cursor from disappearing as the node containing it is replaced
        selection.collapse( anchor, offset );
      } else {
        node.removeAttribute( "style" );
      }
    }
  }

  // the rest only applies to Firefox and other Gecko-based browsers
  if ( !GECKO )
    return;

  // if you're typing the text of an <h3> title and you hit enter, the text cursor will skip a line
  // and then move back up a line when you start typing again. to prevent this behavior, remove an
  // extra <br> tag when this situation is detected before the current node: <h3><br>
  if ( this.iframe.contentWindow && this.iframe.contentWindow.getSelection ) {
    var selection = this.iframe.contentWindow.getSelection();
    var range = selection.getRangeAt( 0 );
    var startOffset = range.startOffset;

    var node = range.startContainer.childNodes[ startOffset ];
    if ( node && node.previousSibling && node.previousSibling.previousSibling &&
         node.previousSibling.nodeName == "BR" &&
         node.previousSibling.previousSibling.nodeName == "H3" ) {
      removeElement( node.previousSibling );
      if ( node.nodeName != "BR" )
        insertSiblingNodesBefore( node, createDOM( "br" ) );
      else
        this.resize();
    }
  }
}

Editor.prototype.mouse_clicked = function ( event ) {
  this.link_started = null;
  var self = this;

  function handle_click( event ) {
    // we only want to deal with left mouse button clicks
    if ( event.mouse().button.middle || event.mouse().button.right )
      return false;

    // search through the tree of elements containing the clicked target. if a link isn't found, bail
    var link = event.target()
    if ( !link ) false;

    while ( link.nodeName != "A" ) {
      link = link.parentNode;
      if ( !link )
        return false;
    }
    if ( !link.href ) return false;

    // links with targets are considered to be external links pointing outside of this wiki
    if ( link.target ) {
      // if this is a read-only editor, bail and let the browser handle the link normally
      if ( !self.edit_enabled ) return true;
      
      // otherwise, this is a read-write editor, so we've got to launch the external link ourselves.
      // note that this ignores what the link target actually contains and assumes it's "_new"
      window.open( link.href );
      event.stop();
      return true;
    }

    // special case for links to uploaded files
    if ( !link.target && /\/files\//.test( link.href ) ) {
      if ( !/\/files\/new$/.test( link.href ) ) {
        window.open( link.href );
        event.stop();
      }
      return true;
    }

    event.stop();

    // load the note corresponding to the clicked link
    var query = parse_query( link );
    var title = link_title( link, query );
    var id = query.note_id;
    signal( self, "load_editor", title, id, null, null, link, self.iframe );
    return true;
  }

  var link_clicked = handle_click( event );

  // in case the cursor has moved, update the state
  if ( this.edit_enabled )
    signal( this, "state_changed", this, link_clicked );
}

HOVER_DURATION_MILLISECONDS = 1000;

Editor.prototype.mouse_hovered = function ( event ) {
  // search through the tree of elements containing the hover target for a link
  var link = event.target()
  if ( !link ) false;

  while ( link.nodeName != "A" ) {
    link = link.parentNode;
    if ( !link )
      break;
  }
  if ( !link || !link.href )
    link = null;

  var self = this;
  var hover_target = link || event.target();
  this.hover_target = hover_target;

  if ( this.hover_timer )
    clearTimeout( this.hover_timer );

  this.hover_timer = setTimeout( function () { self.mouse_hover_timeout( hover_target ) }, HOVER_DURATION_MILLISECONDS );
}

Editor.prototype.mouse_hover_timeout = function ( hover_target ) {
  // if the mouse is hovering over the same target that it was when the timer started
  if ( hover_target == this.hover_target )
    signal( this, "mouse_hovered", hover_target );
}

Editor.prototype.mouse_dragged = function ( event ) {
  // reset the hover timer to prevent a mouse hover from being registered while the mouse is being dragged
  if ( this.hover_timer ) {
    var self = this;
    clearTimeout( this.hover_timer );
    this.hover_timer = setTimeout( function () { self.mouse_hover_timeout( self.hover_target ) }, HOVER_DURATION_MILLISECONDS );
  }
}

Editor.prototype.scrape_title = function () {
  // scrape the note title out of the editor
  var heading = getFirstElementByTagAndClassName( "h3", null, this.document || this.div );
  if ( heading )
    var title = scrapeText( heading );
  else
    var title = "";

  // issue a signal that the title has changed and save off the new title
  if ( this.edit_enabled )
    signal( this, "title_changed", this, this.title, title );
  this.title = title;
}

Editor.prototype.focused = function () {
  this.create_iframe();

  signal( this, "focused", this );
}

Editor.prototype.blurred = function () {
  this.scrape_title();

  this.create_div();
}

Editor.title_placeholder_char = "\u200b";
Editor.title_placeholder_pattern = /\u200b/g;
Editor.title_placeholder_html = "&#8203;&#8203;";

Editor.prototype.empty = function () {
  if ( this.div )
    var node = this.div;
  else if ( this.document && this.document.body )
    var node = this.document.body;
  else
    return true;

  return ( scrapeText( node ).replace( Editor.title_placeholder_pattern, "" ).length == 0 );
}

Editor.prototype.insert_link = function ( url ) {
  // get the current selection, which is the link title
  if ( this.iframe.contentWindow && this.iframe.contentWindow.getSelection ) { // browsers such as Firefox
    var selection = this.iframe.contentWindow.getSelection();

    // if no text is selected, then insert a link with two zero-width spaces as the title. then,
    // position the text cursor between the two zero-width spaces. yes, this really is necessary.
    // it ensures that the next character typed in WebKit becomes part of the link title.
    if ( selection.toString().length == 0 ) {
      this.insert_html( '<a href="' + url + '" id="new_link">' + Editor.title_placeholder_html + '</a>' );
      var link = withDocument( this.document, function () { return getElement( "new_link" ); } );
      link.removeAttribute( "id" );
      selection.selectAllChildren( link );
      selection.collapse( link.firstChild, 1 );
      this.link_started = link;
    // otherwise, just create a link with the selected text as the link title
    } else {
      this.link_started = null;
      this.exec_command( "createLink", url );
      return this.find_link_at_cursor();
    }
  } else if ( this.document.selection ) { // browsers such as IE
    var range = this.document.selection.createRange();

    // if no text is selected, then insert a link with a placeholder space as the link title, and
    // then select it
    if ( range.text.length == 0 ) {
      range.text = " ";
      range.moveStart( "character", -1 );
      range.select();
      this.exec_command( "createLink", url );
      this.link_started = this.find_link_at_cursor();
    } else {
      this.link_started = null;
      this.exec_command( "createLink", url );
      return this.find_link_at_cursor();
    }
  }
}

Editor.prototype.start_link = function () {
  return this.insert_link( "/notebooks/" + this.notebook_id + "?note_id=new" );
}

Editor.prototype.start_file_link = function () {
  return this.insert_link( "/files/new" );
}

Editor.prototype.end_link = function () {
  this.link_started = null;
  var link = this.find_link_at_cursor();

  if ( this.iframe.contentWindow && this.iframe.contentWindow.getSelection ) { // browsers such as Firefox
    this.exec_command( "unlink" );

    // necessary to actually end a link in WebKit. the side-effect is that the cursor jumps to the
    // end of the link if it's not already there
    if ( link && WEBKIT ) {
      var selection = this.iframe.contentWindow.getSelection();
      var sentinel = this.document.createTextNode( Editor.title_placeholder_char );
      insertSiblingNodesAfter( link, sentinel );
      selection.collapse( sentinel, 1 );
    }
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
    range.parentElement().appendChild( span );
    range.moveToElementText( span );
    range.select();
    range.pasteHTML( "" );
  }

  return link;
}

Editor.prototype.find_link_at_cursor = function () {
  if ( this.iframe && this.iframe.contentWindow && this.iframe.contentWindow.getSelection ) { // browsers such as Firefox
    var selection = this.iframe.contentWindow.getSelection();
    var link = selection.anchorNode;
    if ( !link ) return null;

    while ( link.nodeName != "A" ) {
      link = link.parentNode;
      if ( !link )
        break;
    }

    if ( link != this.link_started )
      this.link_started = null;
    if ( link ) return link;

    // well, that didn't work, so try the selection's focus node instead
    link = selection.focusNode;

    while ( link.nodeName != "A" ) {
      link = link.parentNode;
      if ( !link ) {
        this.link_started = null;
        return null;
      }
    }

    if ( link != this.link_started )
      this.link_started = null;
    return link;
  } else if ( this.document && this.document.selection ) { // browsers such as IE
    var range = this.document.selection.createRange();
    var link = range.parentElement();

    while ( link.nodeName != "A" ) {
      link = link.parentNode;
      if ( !link ) {
        this.link_started = null;
        return null;
      }
    }

    if ( link != this.link_started )
      this.link_started = null;
    return link;
  }

  this.link_started = null;
  return null;
}

Editor.prototype.focus = function () {
  if ( /Opera/.test( navigator.userAgent ) )
    this.iframe.focus();
  else
    this.iframe.contentWindow.focus();
}

Editor.prototype.contents = function () {
  if ( this.div ) {
    var static_contents = getFirstElementByTagAndClassName( "span", "static_note_contents", this.div );
    if ( static_contents )
      return static_contents.innerHTML;
  }

  if ( this.document && this.document.body )
    return this.document.body.innerHTML;

  return this.initial_text || "";
}

// return true if the given state_name is currently enabled, optionally using a given list of node
// names
Editor.prototype.state_enabled = function ( state_name, node_names ) {
  if ( !this.edit_enabled )
    return false;

  state_name = state_name.toLowerCase();
  if ( !node_names )
    node_names = this.current_node_names();

  for ( var i in node_names ) {
    var node_name = node_names[ i ];
    if ( node_name == state_name )
      return true;
  }

  return false;
}

// return a list of names for all the nodes containing the cursor
Editor.prototype.current_node_names = function () {
  var node_names = new Array();

  if ( !this.edit_enabled || !this.iframe || !this.document )
    return node_names;

  // to determine whether the specified state is enabled, see whether the current selection is
  // contained (directly or indirectly) by a node of the appropriate type (e.g. "h3", "a", etc.)
  var node;
  if ( window.getSelection ) { // browsers such as Firefox
    var selection = this.iframe.contentWindow.getSelection();
    if ( selection.rangeCount > 0 )
      var range = selection.getRangeAt( 0 );
    else
      var range = this.document.createRange();
    node = range.endContainer;
  } else if ( this.document.selection ) { // browsers such as IE
    var range = this.document.selection.createRange();
    node = range.parentElement();
  }

  while ( node ) {
    var name = node.nodeName.toLowerCase();

    if ( name == "strong" ) name = "b";
    if ( name == "em" ) name = "i";

    if ( name != "a" || node.href )
      node_names.push( name );

    node = node.parentNode;
  }

  return node_names;
}

Editor.prototype.shutdown = function( event ) {
  signal( this, "title_changed", this, this.title, null );
  this.closed = true;
  var note_controls = this.note_controls;

  if ( this.iframe ) {
    var iframe = this.iframe;
    this.iframe = null;
    disconnectAll( this );
    disconnectAll( this.delete_button );
    disconnectAll( this.changes_button );
    disconnectAll( this.options_button );
    disconnectAll( this.hide_button );
    disconnectAll( iframe );
    var editor_node = iframe;
  }

  if ( this.document ) {
    disconnectAll( this.document.body );
    disconnectAll( this.document );
  }

  if ( this.div ) {
    disconnectAll( this.div );
    var editor_node = this.div;
    this.div = null;
  }

  blindUp( editor_node, options = { "duration": 0.25, afterFinish: function () {
    try {
      removeElement( note_controls );
      removeElement( editor_node );
    } catch ( e ) { }
  } } );
}

Editor.prototype.summarize = function () {
  if ( this.div )
    return summarize_html( scrapeText( this.div ), this.title );

  if ( this.document && this.document.body )
    return summarize_html( scrapeText( this.document.body ), this.title );

  return "";
}

function summarize_html( html, title ) {
  var span = createDOM( "span", {} );
  span.innerHTML = html;
  var summary = strip( scrapeText( span ) );

  // remove the title (if any) from the summary text
  if ( title && summary.indexOf( title ) == 0 )
    summary = summary.substr( title.length );

  if ( summary.length == 0 )
    return null;

  var MAX_SUMMARY_LENGTH = 40;
  var word_count = 10;

  // split the summary on whitespace
  var words = summary.split( /\s+/ );

  function first_words( words, word_count ) {
    return words.slice( 0, word_count ).join( " " );
  }

  var truncated = false;
  summary = first_words( words, word_count );

  // find a summary less than MAX_SUMMARY_LENGTH and, if possible, truncated on a word boundary
  while ( summary.length > MAX_SUMMARY_LENGTH ) {
    word_count -= 1;
    summary = first_words( words, word_count );

    // if the first word is just ridiculously long, truncate it without finding a word boundary
    if ( word_count == 1 ) {
      summary = summary.substr( 0, MAX_SUMMARY_LENGTH );
      truncated = true;
      break;
    }
  }

  if ( truncated ||  word_count < words.length )
    summary += " ...";

  return summary;
}

// return the given html in a normal form. this makes html string comparisons more accurate
function normalize_html( html ) {
  if ( !html ) return html;

  // remove any "pulldown" attributes, which get added in IE whenever link.pulldown is set
  var normal_html = html.replace( /\s+pulldown="null"/g, "" );

  // convert absolute URLs to the server into relative URLs. accomplish this by removing, for
  // instance, "https://luminotes.com" from any URLs. this is necessary becuase IE insists on
  // converting relative link URLs to absolute URLs
  var base_url = window.location.protocol + "//" + window.location.host;
  normal_html = normal_html.replace( '="' + base_url + '/', '="/' );

  return normal_html;
}

Editor.prototype.dirty = function () {
  var original_html = normalize_html( this.initial_text )
  var current_html = normalize_html( this.contents() );

  if ( current_html == "" || current_html == original_html )
    return false;

  return true;
}

Editor.prototype.mark_clean = function () {
  this.initial_text = this.contents();
}

Editor.prototype.mark_dirty = function () {
  this.initial_text = null;
}

// convenience function for parsing a link that has an href URL containing a query string
function parse_query( link ) {
  if ( !link || !link.href )
    return new Array();

  return parseQueryString( link.href.split( "?" ).pop() );
}

// convenience function for getting a link's title (stripped of whitespace), either from a query
// argument in the href, from the actual link title, or from the link's href
function link_title( link, query ) {
  if ( link && link.target )
    return link.href;

  if ( !query )
    query = parse_query( link );

  var link_title = strip( query.title || scrapeText( link ) );

  // work around an IE quirk in which link titles are sometimes 0xa0
  if ( link_title.charCodeAt( 0 ) == 160 )
    return "";

  return link_title.replace( Editor.title_placeholder_pattern, "" );
}

function normalize_title( title ) {
  return title.replace( Editor.title_placeholder_pattern, "" ) || "untitled note";
}
