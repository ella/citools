from os import mkdir, chdir
from shutil import copytree, ignore_patterns
from tempfile import mkdtemp
from subprocess import check_call, CalledProcessError, PIPE
import os
import os.path
from shutil import rmtree

from unittest import TestCase

from nose.plugins.skip import SkipTest

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
        check_call(['git', 'add', '*'], cwd=self.repo)
        check_call(['git', 'commit', '-a', '-m', "Initial project import"], cwd=self.repo, stdout=PIPE, stderr=PIPE)

        

    def tearDown(self):
        os.chdir(self.oldcwd)

        rmtree(self.holder)

        super(PaverTestCase, self).setUp()
