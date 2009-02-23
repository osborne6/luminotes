from Tags import Div, A, Img, Span, B
from config.Version import VERSION, TRIAL

class Header( Div ):
  def __init__( self, user, first_notebook, login_url, logout_url, note_title, rate_plan = None ):
    title_image = Img(
      src ="/static/images/luminotes_title.png",
      class_ = u"luminotes_title", width = u"193", height = u"60",
      alt = u"Luminotes",
    )

    trial_expired = False
    if TRIAL:
      from pytz import utc
      from datetime import datetime, timedelta
      
      trial_age = datetime.now( tz = utc ) - first_notebook.revision
      if trial_age > timedelta( days = 30 ):
        trial_expired = True

    if rate_plan and rate_plan.get( u"name" ) == u"desktop":
      Div.__init__(
        self,
        Div(
          ( note_title == u"home" ) and title_image or
            A( title_image, href = u"http://luminotes.com/", target = "_new" ),
          Div(
            ( TRIAL and u"trial" or u"" ), u"version", VERSION, u" | ",
            A( u"upgrade", href = u"http://luminotes.com/download", target = "_new", class_ = trial_expired and "trial_upgrade_link" or u"" ), u" | ",
            A( u"community", href = u"http://luminotes.com/community", target = "_new" ), u" | ",
            A( u"blog", href = u"http://luminotes.com/blog/", target = "_new" ), u" | ",
            A( u"close", href = u"/close" ),
            class_ = u"header_links",
          ),
          class_ = u"wide_center_area",
        ),
        id = u"header",
        class_ = u"header",
      )
      return

    Div.__init__(
      self,
      Div(
        ( note_title == u"home" ) and title_image or A( title_image, href = u"/" ),   
        ( login_url and user.username == u"anonymous" ) and Div(
          A(
            u"login",
            href = login_url,
            id = u"login_link",
            class_ = u"bold_link",
          ),
          class_ = u"header_user_links",
        ) or Div(
          u"logged in as %s" % ( user.username or u"a guest" ),
          u" | ",
          ( note_title != u"wiki" ) and first_notebook and Span(
            A(
              u"my wiki",
              href = u"/notebooks/%s" % first_notebook.object_id,
            ),
            u" | ",
          ) or None,
          user.username and note_title == u"wiki" and Span(
            A(
              u"settings",
              href = u"#",
              title = u"Update your account settings.",
              id = u"settings_link",
            ),
            " | ",
          ) or None,
          A(
            u"logout",
            href = logout_url,
            id = u"logout_link",
            title = u"Sign out of your account.",
          ),
          class_ = u"header_user_links",
        ),
        Div(
          ( note_title == u"home" ) and Span( u"home", class_ = u"bold_link" ) or A( u"home", href = u"/" ), u" | ",
          ( note_title == u"tour" ) and Span( u"tour", class_ = u"bold_link" ) or A( u"tour", href = u"/tour" ), u" | ",
          ( user.username in ( None, u"anonymous" ) ) and Span( ( note_title == u"wiki" ) and Span( u"demo", class_ = u"bold_link" ) or A( u"demo", href = u"/users/demo" ), u" | " ) or None,
          ( note_title == u"community" ) and Span( u"community", class_ = u"bold_link" ) or A( u"community", href = u"/community" ), u" | ",
          ( note_title == u"download" ) and Span( u"download", class_ = u"bold_link" ) or \
          A(
            u"download",
            href = u"/download",
            title = u"Download Luminotes to run on your own computer.",
            class_ = u"bold_link",
          ),
          " | ",
          ( user.username and user.username != u"anonymous" ) and Span(
            A(
              u"upgrade",
              href = u"/pricing",
              title = u"Upgrade your Luminotes account.",
              class_ = u"bold_link",
            ),
          ) or Span(
            ( note_title == u"pricing" ) and Span( u"sign up", class_ = u"bold_link" ) or \
            A(
              u"sign up",
              href = u"/pricing",
              title = u"Sign up for an online Luminotes account.",
              class_ = u"bold_link",
            ),
          ) or None,

          #( note_title == u"support" ) and Span( u"support", class_ = u"bold_link" ) or A( u"support", href = u"/support" ), u" | ",
          #( note_title == u"team" ) and Span( u"team", class_ = u"bold_link" ) or A( u"team", href = u"/meet_the_team" ), u" | ",
          #( note_title == u"blog" ) and Span( u"blog", class_ = u"bold_link" ) or A( u"blog", href = u"/blog" ), u" | ",
          #( note_title == u"privacy" ) and Span( u"privacy", class_ = u"bold_link" ) or A( u"privacy", href = u"/privacy" ),
          class_ = u"header_links",
        ),
        class_ = u"wide_center_area",
      ),
      id = u"header",
      class_ = u"header",
    )

