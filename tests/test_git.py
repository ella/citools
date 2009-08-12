from ConfigParser import SafeConfigParser
from unittest import TestCase

import os
from subprocess import Popen, PIPE
from shutil import rmtree
from tempfile import mkdtemp, mkstemp

from citools.version import fetch_repository

class TestRepositoryFetching(TestCase):

    def setUp(self):
        TestCase.setUp(self)

        self._create_git_repository()
        self._prepare_tagged_repo_with_file(tag="0.1")


    def _create_git_repository(self):
        # create temporary directory and initialize git repository there
        self.repo = mkdtemp(prefix='test_git_')
        self.oldcwd = os.getcwd()
        os.chdir(self.repo)
        proc = Popen(['git', 'init'], stdout=PIPE, stdin=PIPE)
        proc.wait()
        self.assertEquals(0, proc.returncode)

        # also setup dummy name / email for this repo for tag purposes
        proc = Popen(['git', 'config', 'user.name', 'dummy-tester'])
        proc.wait()
        self.assertEquals(0, proc.returncode)
        proc = Popen(['git', 'config', 'user.email', 'dummy-tester@example.com'])
        proc.wait()
        self.assertEquals(0, proc.returncode)

    def _prepare_tagged_repo_with_file(self, tag):
        f = open(os.path.join(self.repo, 'test.txt'), 'wb')
        f.write("test")
        f.close()

        proc = Popen(["git", "add", "*"])
        proc.wait()
        self.assertEquals(0, proc.returncode)

        proc = Popen(['git', 'commit', '-m', '"dummy"'], stdout=PIPE, stdin=PIPE)
        proc.wait()
        self.assertEquals(0, proc.returncode)

        proc = Popen(['git', 'tag', '-m', '"tagging"', '-a', tag], stdout=PIPE, stdin=PIPE)
        proc.wait()
        self.assertEquals(0, proc.returncode)

    def test_cached_repo_is_not_fetched_again(self):
        invalid_repo_uri = "ssh://user@nonexisting.example.com/repository"

        handle, cache_file = mkstemp(prefix="config_git_", suffix=".ini")
        f = open(cache_file, "w+b")
        f.write("""[%s]
cache_dir = %s
""" % (invalid_repo_uri, self.repo))
        f.close()

        self.assertEquals(self.repo, fetch_repository(repository=invalid_repo_uri,
            cache_config_dir=os.path.dirname(cache_file),
            cache_config_file_name=os.path.basename(cache_file)
        ))

    def test_fetching_creates_cache(self):
        repo_uri = os.path.abspath(self.repo)
        cache_dir = mkdtemp(prefix="test_git_")

        dir = fetch_repository(
            repository = repo_uri,
            cache_config_dir = cache_dir
        )

        config_file = os.path.join(cache_dir, "cached_repositories.ini")
        self.assertTrue(os.path.exists(config_file))

        parser = SafeConfigParser()
        parser.read([config_file])

        self.assertEquals(dir, parser.get(repo_uri, "cache_dir"))

        rmtree(cache_dir)

    def tearDown(self):
        TestCase.tearDown(self)
        # delete temporary repository and restore ENV vars after update
        rmtree(self.repo)
        os.chdir(self.oldcwd)
