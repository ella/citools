
from unittest import TestCase

import os
from subprocess import Popen, PIPE, check_call
from shutil import rmtree
from StringIO import StringIO
from tempfile import mkdtemp

from citools.version import (
    compute_version, get_git_describe, replace_version, compute_meta_version,
    sum_versions, fetch_repository
)

class TestVersioning(TestCase):

    def test_after_tag(self):
        self.assertEquals((0, 7, 20), compute_version('tools-0.7-20-g1754c3f'))

    def test_after_tag_without_name(self):
        self.assertEquals((0, 7, 20), compute_version('0.7-20-g1754c3f'))

    def test_after_tag_with_project_suffix(self):
        self.assertEquals((0, 7, 20), compute_version('0.7-our-tools-project-20-g1754c3f'))

    def test_on_tag(self):
        self.assertEquals((0, 7, 0), compute_version('tools-0.7'))

    def test_on_tag_with_suffix(self):
        self.assertEquals((0, 7, 0), compute_version('0.7-our-tools-project'))

    def test_first_release_tag(self):
        self.assertEquals((0, 0, 1), compute_version('0.0'))

    def test_bad_release_tag(self):
        self.assertRaises(ValueError, compute_version, 'arghpaxorgz-zsdf')

    def test_on_tag_with_suffix_four_digits(self):
        self.assertEquals((0, 7, 3, 0), compute_version('0.7.3-our-tools-project'))

    def test_project_with_digit_in_name(self):
        self.assertEquals((9, 7, 3, 45, 532, 11, 44), compute_version('log4j-9.7.3.45.532.11-44-g1754c3f'))

    def test_multiple_digit_versin(self):
        self.assertEquals((0, 10, 2), compute_version('log4j-0.10-2-gbb6aff8'))

    def test_version_replacing_three_digits(self):
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

    def test_version_replacing_lot_digits(self):
        source = StringIO("""arakadabra
blah blah
VERSION = (1, 2, 3)
x = (3, 2, 1)
for i in x:
    print 'olah'""")

        expected_output = """arakadabra
blah blah
VERSION = (9, 7, 3, 45, 532, 11, 44)
x = (3, 2, 1)
for i in x:
    print 'olah'"""

        self.assertEquals(expected_output, ''.join(replace_version(source, version=(9, 7, 3, 45, 532, 11, 44))))

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


    def test_pattern_used_to_filter_everything_acting_like_without_tag(self):
        self.prepare_tagged_repo_with_file(tag='0.1-lol')

        self.assertEquals('0.0', get_git_describe(accepted_tag_pattern='myproject-*'))


    def _check_filtering_works(self, tag, retag, search_pattern, expected_result_start):
        self.prepare_tagged_repo_with_file(tag=tag)

        # create a commit
        f = open(os.path.join(self.repo, 'test.txt'), 'wb')
        f.write("test test")
        f.close()

        check_call(['git', 'add', '*'])
        check_call(['git', 'commit', '-a', '-m', '"dummy"'], stdout=PIPE)
        check_call(['git', 'tag', '-m', '"tagging"', '-a', retag])

        describe = get_git_describe(accepted_tag_pattern=search_pattern)
        self.assertTrue(describe.startswith(expected_result_start), "Retrieved bad describe %s" % describe)

    def test_pattern_used_to_filter_only_matching_tags(self):
        self._check_filtering_works(tag='release/project-0.1', retag="xxxx",
            search_pattern='release/project-[0-9]*',
            expected_result_start='release/project-0.1-1')

    def test_pattern_used_to_separate_bad_suffixes(self):
        self._check_filtering_works(tag='project-0.1',
            retag="project-meta-0.1",
            search_pattern='project-[0-9]*',
            expected_result_start='project-0.1-1')

    def test_pattern_used_to_separate_bad_prefixes(self):
        self._check_filtering_works(tag='project-0.1',
            retag="myproject-0.1",
            search_pattern='project-[0-9]*',
            expected_result_start='project-0.1-1')

    def tearDown(self):
        TestCase.tearDown(self)
        # delete temporary repository and restore ENV vars after update
        rmtree(self.repo)
        os.chdir(self.oldcwd)

class TestMetaRepository(TestCase):

    def setUp(self):
        TestCase.setUp(self)

        self.oldcwd = os.getcwd()

        self.repo_parent = mkdtemp(prefix='test_git_')
        self.prepare_repository(self.repo_parent, "meta-project-0.1")

        self.repo_one = mkdtemp(prefix='test_git_')
        self.prepare_repository(self.repo_one, "project-1.0.59", number_of_commits_since=1)

        self.repo_two = mkdtemp(prefix='test_git_')
        self.prepare_repository(self.repo_two, "secondproject-2.0", file_name="second.txt", number_of_commits_since=12)

        os.chdir(self.repo_parent)

    def prepare_repository(self, directory, tag_name, number_of_commits_since=0, file_name="test.txt", testomation_branch=True):
        """
        Prepare a repository inside given directory, with first commit tagged
        as tag_name and with additional commits

        With testomation_branch set to true, one additional commit is given in testomation branch
        """
        os.chdir(directory)
        check_call(['git', 'init'], stdout=PIPE, stdin=PIPE)
        
        # configure me
        check_call(['git', 'config', 'user.email', 'testcase@example.com'])
        check_call(['git', 'config', 'user.name', 'Testing Testorz'])

        # create a commit
        f = open(os.path.join(directory, file_name), 'wb')
        f.write("test test")
        f.close()

        check_call(['git', 'add', '*'])
        check_call(['git', 'commit', '-a', '-m', '"dummy"'], stdout=PIPE, stdin=PIPE)
        check_call(['git', 'tag', '-a', '-m', '"dummy"', tag_name], stdout=PIPE, stdin=PIPE)

        if number_of_commits_since > 0:
            for i in xrange(0, number_of_commits_since):
                f = open(os.path.join(directory, file_name), 'wb')
                for n in xrange(0, i):
                    f.write("test\n")
                f.close()
                check_call(['git', 'add', '*'])
                check_call(['git', 'commit', '-a', '-m', '%s commit since' % i], stdout=PIPE, stdin=PIPE)

        if testomation_branch:
            check_call(['git', 'checkout', '-b', 'testomation'], stdout=PIPE, stderr=PIPE)

            f = open(os.path.join(directory, file_name), 'wb')
            f.write("testomation test\n")
            f.close()
            check_call(['git', 'add', '*'])
            check_call(['git', 'commit', '-a', '-m', 'testomation test'], stdout=PIPE, stderr=PIPE)

            # backward compatibility: go back to master
            check_call(['git', 'checkout', 'master'], stdout=PIPE, stderr=PIPE)


    def test_proper_child_version(self):
        self.assertEquals((1, 0, 59, 1), compute_version(get_git_describe(repository_directory=self.repo_one, fix_environment=True)))

    def test_proper_second_child_version(self):
        self.assertEquals((2, 0, 12), compute_version(get_git_describe(repository_directory=self.repo_two, fix_environment=True)))

    def test_computing_meta_version(self):
        # 0.1.0 is my version
        # 1.0.59.1 is first child
        # 2.0.12 is second child
        # => 3.1.71.1
        self.assertEquals((3, 1, 71, 1), compute_meta_version(dependency_repositories=[{'url':self.repo_one}, {'url' : self.repo_two}]))


    def test_computing_meta_version_accepts_branch(self):
        # 0.1.0 is my version (my deps are testomation, but I'm at master!)
        # 1.0.59.2 is first child
        # 2.0.13 is second child
        # => 3.1.72.2

        self.assertEquals((3, 1, 72, 2), compute_meta_version(dependency_repositories=[
            {
                'url':self.repo_one,
                'branch' : 'testomation',
            },
            {
                'url' : self.repo_two,
                'branch' : 'testomation',
            }
        ]))

    def test_current_branch_is_default_for_deps(self):
        # 0.1.1 is my version
        # 1.0.59.2 is first child
        # 2.0.13 is second child
        # => 3.1.73.2

        check_call(['git', 'checkout', 'testomation'], stdout=PIPE, stderr=PIPE)

        self.assertEquals((3, 1, 73, 2), compute_meta_version(dependency_repositories=[
            {
                'url':self.repo_one,
            },
            {
                'url' : self.repo_two,
            }
        ]))

    def test_repository_fetching(self):
        dir = mkdtemp()
        repodir = fetch_repository(repository=self.repo_two, workdir=dir)
        self.assertEquals([".git", "second.txt"].sort(), os.listdir(repodir).sort())
        rmtree(dir)

    def test_fetched_repository_has_same_version(self):
        dir = mkdtemp()
        repodir = fetch_repository(repository=self.repo_two, workdir=dir)
        self.assertEquals((2, 0, 12), compute_version(get_git_describe(repository_directory=repodir, fix_environment=True)))
        rmtree(dir)

    def tearDown(self):
        TestCase.tearDown(self)
        os.chdir(self.oldcwd)

        rmtree(self.repo_parent)
        rmtree(self.repo_one)
        rmtree(self.repo_two)

class TestVersionNumberManipulations(TestCase):

    def test_sum_same_length(self):
        self.assertEquals((0, 2), sum_versions((0, 1), (0, 1)))

    def test_sum_various_length(self):
        self.assertEquals((1, 3, 3), sum_versions((1, 2, 3), (0, 1)))

    def test_sum_bad_number(self):
        self.assertRaises(ValueError, sum_versions, (1, 2, 3), (0, -23))

    def test_sum_bad_number_in_first_version(self):
        self.assertRaises(ValueError, sum_versions, (-1, 2, 3), (0, 128, 0))


