import cgi
from config.Version import VERSION


general_error_script = \
  """
  withDocument( window.parent.document, function () { var frame = getFirstElementByTagAndClassName( "iframe", "upload_frame" ); if ( frame && frame.pulldown ) frame.pulldown.cancel_due_to_error( "%s" ); } );
  """


quota_error_script = \
  """
  withDocument( window.parent.document, function () { var frame = getFirstElementByTagAndClassName( "iframe", "upload_frame" ); if ( frame && frame.pulldown ) frame.pulldown.cancel_due_to_quota(); } );
  """
