import fnmatch
import os
from os import chdir
import os.path
from shutil import rmtree, Error, copy2, copystat
import socket
from subprocess import check_call, CalledProcessError, PIPE
from tempfile import mkdtemp

from unittest import TestCase

from nose.plugins.skip import SkipTest

try:
    HOST = socket.gethostbyname('localhost')
except socket.error:
    HOST = 'localhost'

###########
### copytree and ignore_patterns copied from py2.6 source to be usable in py2.5
### Copyright PSF and under Python license
###########

def ignore_patterns(*patterns):
    """Function that can be used as copytree() ignore parameter.

    Patterns is a sequence of glob-style patterns
    that are used to exclude files"""
    def _ignore_patterns(path, names):
        ignored_names = []
        for pattern in patterns:
            ignored_names.extend(fnmatch.filter(names, pattern))
        return set(ignored_names)
    return _ignore_patterns

def copytree(src, dst, symlinks=False, ignore=None):
    """Recursively copy a directory tree using copy2().

    The destination directory must not already exist.
    If exception(s) occur, an Error is raised with a list of reasons.

    If the optional symlinks flag is true, symbolic links in the
    source tree result in symbolic links in the destination tree; if
    it is false, the contents of the files pointed to by symbolic
    links are copied.

    The optional ignore argument is a callable. If given, it
    is called with the `src` parameter, which is the directory
    being visited by copytree(), and `names` which is the list of
    `src` contents, as returned by os.listdir():

        callable(src, names) -> ignored_names

    Since copytree() is called recursively, the callable will be
    called once for each directory that is copied. It returns a
    list of names relative to the `src` directory that should
    not be copied.

    XXX Consider this example code rather than the ultimate tool.

    """
    names = os.listdir(src)
    if ignore is not None:
        ignored_names = ignore(src, names)
    else:
        ignored_names = set()

    os.makedirs(dst)
    errors = []
    for name in names:
        if name in ignored_names:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                copytree(srcname, dstname, symlinks, ignore)
            else:
                copy2(srcname, dstname)
            # XXX What about devices, sockets etc.?
        except (IOError, os.error), why:
            errors.append((srcname, dstname, str(why)))
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except Error, err:
            errors.extend(err.args[0])
    try:
        copystat(src, dst)
    except OSError, why:
        if WindowsError is not None and isinstance(why, WindowsError):
            # Copying file access times may fail on Windows
            pass
        else:
            errors.extend((src, dst, str(why)))
    if errors:
        raise Error, errors





class MongoTestCase(TestCase):
    def setUp(self):
        try:
            from pymongo.errors import ConnectionFailure
            from citools.mongo import get_mongo_and_database_connections
        except ImportError, e:
            import traceback as t
            raise SkipTest("Error when importing dependencies (pymongo not installed?): %s" % t.format_exc())
        connection_arguments = {
            "hostname" : os.environ.get("MONGODB_HOSTNAME", "localhost"),
            "database" : os.environ.get("MONGODB_DATABASE_NAME", "test_citools")
        }

        if os.environ.get("MONGODB_PORT", None):
            connection_arguments['port'] = os.environ.get("MONGODB_PORT", None)

        if os.environ.get("MONGODB_USERNAME", None):
            connection_arguments['username'] = os.environ.get("MONGODB_USERNAME", None)

        if os.environ.get("MONGODB_PASSWORD", None):
            connection_arguments['password'] = os.environ.get("MONGODB_PASSWORD", None)

        try:
            self.database, self.connection = get_mongo_and_database_connections(
                **connection_arguments
            )
        except ConnectionFailure:
            raise SkipTest("Cannot connect to mongo database, check your settings")

    def tearDown(self):
        self.connection.drop_database(self.database)

class PaverTestCase(TestCase):
    """
    This is true integration test and is kind of creepy.

    It will take example project in expected layout, placed in test/exproject,
    copy it in temporary environment, where it will be taken under git version control.

    Also provide handy functions to create commits for further version tests.
    """

    def setUp(self):
        super(PaverTestCase, self).setUp()
        self.oldcwd = os.getcwd()

        self.example_project_source = os.path.abspath(os.path.join(os.path.dirname(__file__), 'exproject'))

        if not self.example_project_source:
            raise ValueError("Cannot find example project, WTF?")

        try:
            check_call(['git', '--help'], stdout=PIPE, stderr=PIPE)
        except CalledProcessError:
            raise SkipTest("git must be available and in $PATH in order to preform this test")

        self.holder = mkdtemp(prefix='test-repository-')
        self.repo = os.path.abspath(os.path.join(self.holder, 'exproject'))

        copytree(self.example_project_source, self.repo, ignore=ignore_patterns('*.pyc', '*.pyo'))
        chdir(self.repo)

        check_call(['git', 'init'], cwd=self.repo, stdout=PIPE, stderr=PIPE)

        # configure me
        check_call(['git', 'config', 'user.email', 'testcase@example.com'], cwd=self.repo)
        check_call(['git', 'config', 'user.name', 'Testing Testorz'], cwd=self.repo, stdout=PIPE, stderr=PIPE)


        check_call(['git', 'add', '*'], cwd=self.repo)
        check_call(['git', 'commit', '-a', '-m', "Initial project import"], cwd=self.repo, stdout=PIPE, stderr=PIPE)

        

    def tearDown(self):
        os.chdir(self.oldcwd)

        rmtree(self.holder)

        super(PaverTestCase, self).setUp()

try:

    #######
    ### FTPd, thread-based wrapper around pyftpdlib's ftpserver
    ### taken from pyftpdlib test suite. See http://code.google.com/p/pyftpdlib/
    ### Copyright Giampaolo Rodola <g.rodola@gmail.com>
    ### Distributed under MIT license
    ### __init__ args added by Almad <bugs@almad.net>
    #######

    from pyftpdlib import ftpserver
    import threading
    
    class FTPd(threading.Thread):
        """A threaded FTP server used for running tests.

        This is basically a modified version of the FTPServer class which
        wraps the polling loop into a thread.

        The instance returned can be used to start(), stop() and
        eventually re-start() the server.
        """
        handler = ftpserver.FTPHandler

        def __init__(self, host=HOST, port=0, verbose=False, user='test', passwd='test', home='/tmp'):
            threading.Thread.__init__(self)
            self.__serving = False
            self.__stopped = False
            self.__lock = threading.Lock()
            self.__flag = threading.Event()

            if not verbose:
                ftpserver.log = ftpserver.logline = lambda x: x
                
            authorizer = ftpserver.DummyAuthorizer()
            authorizer.add_user(user, passwd, home, perm='elradfmw')  # full perms
            authorizer.add_anonymous(home)
            self.handler.authorizer = authorizer
            self.server = ftpserver.FTPServer((host, port), self.handler)
            self.host, self.port = self.server.socket.getsockname()[:2]

        def __repr__(self):
            status = [self.__class__.__module__ + "." + self.__class__.__name__]
            if self.__serving:
                status.append('active')
            else:
                status.append('inactive')
            status.append('%s:%s' % self.server.socket.getsockname()[:2])
            return '<%s at %#x>' % (' '.join(status), id(self))

        def start(self, timeout=0.01, use_poll=False, map=None):
            """Start serving until an explicit stop() request.
            Polls for shutdown every 'timeout' seconds.
            """
            if self.__serving:
                raise RuntimeError("Server already started")
            if self.__stopped:
                # ensure the server can be started again
                FTPd.__init__(self, self.server.socket.getsockname(), self.handler)
            self.__timeout = timeout
            self.__use_poll = use_poll
            self.__map = map
            threading.Thread.start(self)
            self.__flag.wait()

        def run(self):
            self.__serving = True
            self.__flag.set()
            while self.__serving:
                self.__lock.acquire()
                self.server.serve_forever(timeout=self.__timeout, count=1,
                                          use_poll=self.__use_poll, map=self.__map)
                self.__lock.release()
            self.server.close_all(ignore_all=True)

        def stop(self):
            """Stop serving (also disconnecting all currently connected
            clients) by telling the serve_forever() loop to stop and
            waits until it does.
            """
            if not self.__serving:
                raise RuntimeError("Server not started yet")
            self.__serving = False
            self.__stopped = True
            self.join()

except ImportError:
    pass
