import cgi


def stream_progress( uploading_file, filename, fraction_reported ):
  """
  Stream a progress meter as a file uploads.
  """
  progress_bytes = 0
  progress_width_em = 20
  tick_increment = 0.01
  progress_bar = u'<img src="/static/images/tick.png" style="width: %sem; height: 1em;" id="progress_bar" />' % \
    ( progress_width_em * tick_increment )

  yield \
    u"""
    <html>
    <head>
      <link href="/static/css/upload.css" type="text/css" rel="stylesheet" />
      <script type="text/javascript" src="/static/js/MochiKit.js"></script>
      <meta content="text/html; charset=UTF-8" http_equiv="content-type" />
    </head>
    <body>
    """

  base_filename = filename.split( u"/" )[ -1 ].split( u"\\" )[ -1 ]
  yield \
    u"""
    <div class="field_label">uploading %s: </div>
    <table><tr>
    <td><div id="progress_border">
    %s
    </div></td>
    <td></td>
    <td><span id="status"></span></td>
    <td></td>
    <td><input type="submit" id="cancel_button" class="button" value="cancel" onclick="withDocument( window.parent.document, function () { getElement( 'upload_frame' ).pulldown.shutdown( true ); } );" /></td>
    </tr></table>
    <script type="text/javascript">
    function tick( fraction ) {
      setElementDimensions(
        "progress_bar",
        { "w": %s * fraction }, "em"
      );
      if ( fraction >= 1.0 )
        replaceChildNodes( "status", "100%%" );
      else
        replaceChildNodes( "status", Math.floor( fraction * 100.0 ) + "%%" );
    }
    </script>
    """ % ( cgi.escape( base_filename ), progress_bar, progress_width_em )

  if uploading_file:
    received_bytes = 0
    while received_bytes < uploading_file.content_length:
      received_bytes = uploading_file.wait_for_total_received_bytes()
      fraction_done = float( received_bytes ) / float( uploading_file.content_length )

      if fraction_done == 1.0 or fraction_done > fraction_reported + tick_increment:
        fraction_reported = fraction_done
        yield '<script type="text/javascript">tick(%s);</script>' % fraction_reported

    uploading_file.wait_for_complete()

  if fraction_reported < 1.0:
    yield "An error occurred when uploading the file.</body></html>"
    return

  yield \
    u"""
    <script type="text/javascript">
    withDocument( window.parent.document, function () { getElement( "upload_frame" ).pulldown.upload_complete(); } );
    </script>
    </body>
    </html>
    """


stop_upload_script = \
  """
  withDocument( window.parent.document, function () { getElement( 'upload_frame' ).pulldown.shutdown( true, true ); } );
  """


def stream_quota_error():
  yield \
    u"""
    <html>
    <head>
      <link href="/static/css/upload.css" type="text/css" rel="stylesheet" />
      <script type="text/javascript" src="/static/js/MochiKit.js"></script>
      <meta content="text/html; charset=UTF-8" http_equiv="content-type" />
    </head>
    <body>
    <script type="text/javascript">
    %s
    </script>
    </body>
    </html>
    """ % stop_upload_script
