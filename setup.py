import os
import sys
from glob import glob
from distutils.core import setup, Distribution


VERSION = "1.5.0"


def files( path ):
  if sys.platform.startswith( "win" ):
    path = path.replace( "/", "\\" )

  return glob( path )


class Luminotes( Distribution ):
  def __init__( self, attrs ):
    self.ctypes_com_server = []
    self.com_server = []
    self.services = []
    self.windows = [ dict(
      script = "luminotes.py",
      icon_resources = [ ( 0, "static\\images\\luminotes.ico" ) ],
    ) ]
    self.console = []
    self.service = []
    self.isapi = []
    self.zipfile = "lib\luminotes.zip"
    Distribution.__init__( self, attrs )


manifest_template = '''
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
<assemblyIdentity
  version="5.0.0.0"
  processorArchitecture="x86"
  name="%(prog)s"
  type="win32"
/>
<description>%(prog)s Program</description>
<dependency>
  <dependentAssembly>
    <assemblyIdentity
      type="win32"
      name="Microsoft.Windows.Common-Controls"
      version="6.0.0.0"
      processorArchitecture="X86"
      publicKeyToken="6595b64144ccf1df"
      language="*"
    />
  </dependentAssembly>
</dependency>
</assembly>
'''

RT_MANIFEST = 24

luminotes = dict(
  script = "luminotes.py",
  other_resources = [(RT_MANIFEST, 1, manifest_template % dict(prog="Luminotes"))],
  dest_base = r"prog\luminotes")

class InnoScript:
  def __init__(self,
         name,
         lib_dir,
         dist_dir,
         windows_exe_files = [],
         lib_files = [],
         version = "1.0"):
    self.lib_dir = lib_dir
    self.dist_dir = dist_dir
    if not self.dist_dir[-1] in "\\/":
      self.dist_dir += "\\"
    self.name = name
    self.version = version
    self.windows_exe_files = [self.chop(p) for p in windows_exe_files]
    self.lib_files = [self.chop(p) for p in lib_files]

  def chop(self, pathname):
    assert pathname.startswith(self.dist_dir)
    return pathname[len(self.dist_dir):]
  
  def create(self, pathname="dist\\luminotes.iss"):
    self.pathname = pathname
    ofi = self.file = open(pathname, "w")
    print >> ofi, "; WARNING: This script has been created by py2exe. Changes to this script"
    print >> ofi, "; will be overwritten the next time py2exe is run!"
    print >> ofi, r"[Setup]"
    print >> ofi, r"AppName=%s" % self.name
    print >> ofi, r"AppVerName=%s %s" % (self.name, self.version)
    print >> ofi, r"DefaultDirName={pf}\%s" % self.name
    print >> ofi, r"DefaultGroupName=%s" % self.name
    print >> ofi, r"SetupIconFile=static\images\luminotes.ico"
    print >> ofi

    print >> ofi, r"[Files]"
    for path in self.windows_exe_files + self.lib_files:
      print >> ofi, r'Source: "%s"; DestDir: "{app}\%s"; Flags: ignoreversion' % (path, os.path.dirname(path))
    print >> ofi

    print >> ofi, r"[Icons]"
    for path in self.windows_exe_files:
      print >> ofi, r'Name: "{group}\%s"; Filename: "{app}\%s"' % \
          (self.name, path)
    print >> ofi, 'Name: "{group}\Uninstall %s"; Filename: "{uninstallexe}"' % self.name
    print >> ofi

    print >> ofi, r"[UninstallDelete]"
    print >> ofi, r'Type: files; Name: "{app}\luminotes.log"'
    print >> ofi, r'Type: files; Name: "{app}\luminotes_error.log"'
    print >> ofi

    print >> ofi, r"[UninstallRun]"
    print >> ofi, r'Filename: "{app}\luminotes.exe"; Parameters: "-k"; RunOnceId: LuminotesShutdown'

  def compile(self):
    try:
      import ctypes
    except ImportError:
      try:
        import win32api
      except ImportError:
        import os
        os.startfile(self.pathname)
      else:
        print "Ok, using win32api."
        win32api.ShellExecute(0, "compile",
                        self.pathname,
                        None,
                        None,
                        0)
    else:
      print "Cool, you have ctypes installed."
      res = ctypes.windll.shell32.ShellExecuteA(0, "compile",
                            self.pathname,
                            None,
                            None,
                            0)
      if res < 32:
        raise RuntimeError, "ShellExecute failed, error %d" % res



try:
  import py2exe
  from py2exe.build_exe import py2exe

  class Build_installer(py2exe):
    # This class first builds the exe file(s), then creates a Windows installer.
    # You need InnoSetup for it.
    def run(self):
      # generate an initial database file
      try:
        os.remove( "luminotes.db" )
      except OSError:
        pass

      from tools import initdb
      initdb.main( ( "-l", ) )

      # First, let py2exe do it's work.
      py2exe.run(self)

      lib_dir = self.lib_dir
      dist_dir = self.dist_dir
      
      # create the Installer, using the files py2exe has created.
      script = InnoScript("Luminotes",
                lib_dir,
                dist_dir,
                self.windows_exe_files,
                self.lib_files,
                            version = VERSION)
      print "*** creating the inno setup script***"
      script.create()
      print "*** compiling the inno setup script***"
      script.compile()
      # Note: By default the final setup.exe will be in an Output subdirectory.
except ImportError:
  class Build_installer:
    pass


setup(
  name = "Luminotes",
  version = VERSION,
  author = "Dan Helfman",
  author_email = "support@luminotes.com",
  url = "http://luminotes.com",
  description = "personal wiki notebook",
  distclass = Luminotes,
  cmdclass = { "py2exe": Build_installer }, # override default py2exe class
  data_files = [
    ( "", [ "luminotes.db", ] ),
    ( "static/css", files( "static/css/*.*" ) ),
    ( "static/html", files( "static/html/*.*" ) ),
    ( "static/images", files( "static/images/*.*" ) ),
    ( "static/images/toolbar", files( "static/images/toolbar/*.*" ) ),
    ( "static/images/toolbar/small", files( "static/images/toolbar/small/*.*" ) ),
    ( "static/js", files( "static/js/*.*" ) ),
    ( "files", files( "files/.empty" ) ),
  ],
  options = dict(
    py2exe = dict(
      packages = "cherrypy.filters",
      includes = "email.header,simplejson",
      compressed = 1,
      optimize = 2,
    )
  ),
)
