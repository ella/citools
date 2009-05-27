from unittest import TestCase

import os
from subprocess import Popen, PIPE
from shutil import rmtree
from StringIO import StringIO
from tempfile import mkdtemp

from citools.version import get_version, get_git_describe, replace_version

class TestVersioning(TestCase):

    def test_after_tag(self):
        self.assertEquals((0, 7, 20), get_version('tools-0.7-20-g1754c3f'))

    def test_after_tag_without_name(self):
        self.assertEquals((0, 7, 20), get_version('0.7-20-g1754c3f'))

    def test_after_tag_with_project_suffix(self):
        self.assertEquals((0, 7, 20), get_version('0.7-our-tools-project-20-g1754c3f'))

    def test_on_tag(self):
        self.assertEquals((0, 7, 0), get_version('tools-0.7'))

    def test_on_tag_with_suffix(self):
        self.assertEquals((0, 7, 0), get_version('0.7-our-tools-project'))

    def test_first_release_tag(self):
        self.assertEquals((0, 0, 1), get_version('0.0'))

    def test_bad_release_tag(self):
        self.assertRaises(ValueError, get_version, 'arghpaxorgz-zsdf')

    def test_on_tag_with_suffix_four_digits(self):
        self.assertEquals((0, 7, 3, 0), get_version('0.7.3-our-tools-project'))

    def test_version_replacing(self):
        source = StringIO("""arakadabra
blah blah
VERSION = (1, 2, 3)
x = (3, 2, 1)
for i in x:
    print 'olah'""")

        expected_output = """arakadabra
blah blah
VERSION = (0, 0, 1)
x = (3, 2, 1)
for i in x:
    print 'olah'"""

        self.assertEquals(expected_output, ''.join(replace_version(source, version=(0, 0, 1))))

class TestGitVersionRetrieving(TestCase):

    def setUp(self):
        TestCase.setUp(self)

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

    def prepare_tagged_repo_with_file(self, tag):
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

    def test_without_tag(self):
        self.assertEquals('0.0', get_git_describe())

    def test_tag_retrieved(self):
        self.prepare_tagged_repo_with_file(tag='0.1-lol')
        self.assertEquals('0.1-lol', get_git_describe())

    def test_number_of_commit_since_tag(self):
        self.prepare_tagged_repo_with_file(tag='0.1-lol')

        # create a commit
        f = open(os.path.join(self.repo, 'test.txt'), 'wb')
        f.write("test test")
        f.close()

        proc = Popen(['git', 'add', '*'])
        proc.wait()
        self.assertEquals(0, proc.returncode)

        proc = Popen(['git', 'commit', '-a', '-m', '"dummy"'], stdout=PIPE, stdin=PIPE)
        proc.wait()
        self.assertEquals(0, proc.returncode)

        self.assertTrue(get_git_describe().startswith('0.1-lol-1'))

    def tearDown(self):
        TestCase.tearDown(self)
        # delete temporary repository and restore ENV vars after update
        rmtree(self.repo)
        os.chdir(self.oldcwd)
    