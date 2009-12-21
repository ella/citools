from ConfigParser import SafeConfigParser
from unittest import TestCase

import os
from subprocess import Popen, PIPE
from shutil import rmtree
from tempfile import mkdtemp, mkstemp
from datetime import datetime

from citools.git import retrieve_repository_metadata, fetch_repository, filter_parse_date

class GitTestCase(TestCase):
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

    def do_piped_command_for_success(self, command):
        proc = Popen(command, stdout=PIPE, stdin=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()
        self.assertEquals(0, proc.returncode)

        return (stdout, stderr)

    def commit(self, message='dummy'):
        """ Commmit into repository and return commited revision """
        self.do_piped_command_for_success(['git', 'commit', '-a', '-m', '"%s"' % message])
        stdout = self.do_piped_command_for_success(['git', 'rev-parse', 'HEAD'])[0]
        return stdout.strip()

    def tearDown(self):
        TestCase.tearDown(self)
        # delete temporary repository and restore ENV vars after update
        rmtree(self.repo)
        os.chdir(self.oldcwd)

class TestDateParsing(TestCase):

    def test_naive_parsed(self):
        self.assertEquals(datetime(2009, 12, 1, 20, 58, 01), filter_parse_date('Tue Dec 1 20:58:01 2009'))

    def test_tz_parsed(self):
        self.assertEquals(datetime(2009, 12, 1, 20, 58, 01), filter_parse_date('Tue Dec 1 20:58:01 2009 +0100'))

class TestRepositoryFetching(GitTestCase):

    def setUp(self):
        TestCase.setUp(self)

        self._create_git_repository()
        self._prepare_tagged_repo_with_file(tag="0.1")


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


class TestHistoryMetadataRetrieval(GitTestCase):
    def setUp(self):
        TestCase.setUp(self)

        self._create_git_repository()
        self.revisions = self._prepare_branched_repository()

    def _prepare_branched_repository(self):
        """
        Create git repository, created in order:
     
     6
    |  \
    5   3
    |   |
    4   2
     | /
     1
        """
        revisions = []
        # 1
        f = open(os.path.join(self.repo, 'test.txt'), 'wb')
        f.write("test")
        f.close()

        self.do_piped_command_for_success(["git", "add", "*"])
        revisions.append(self.commit(message="1"))

        # 2

        self.do_piped_command_for_success(["git", "checkout", "-b", "new_branch"])

        f = open(os.path.join(self.repo, 'test.txt'), 'wb')
        f.write("changed")
        f.close()

        revisions.append(self.commit(message="2"))

        # 3
        f = open(os.path.join(self.repo, 'test.txt'), 'wb')
        f.write("changed in new_branch again")
        f.close()

        revisions.append(self.commit(message="3"))

        # 4
        self.do_piped_command_for_success(["git", "checkout", "master"])

        f = open(os.path.join(self.repo, 'test2.txt'), 'wb')
        f.write("new")
        f.close()

        self.do_piped_command_for_success(["git", "add", "*"])

        revisions.append(self.commit(message="4"))

        # 5
        self.do_piped_command_for_success(["git", "checkout", "master"])

        f = open(os.path.join(self.repo, 'test2.txt'), 'wb')
        f.write("changed in master")
        f.close()

        revisions.append(self.commit(message="5"))

        #6
        self.do_piped_command_for_success(["git", "merge", "new_branch"])

        return revisions

    def _prepare_shorter_tree(self, revision):
        self.do_piped_command_for_success(["git", "checkout", str(revision)])
        self.do_piped_command_for_success(["git", "reset", "--hard"])

    def _get_metadata_for_revision_4(self):
        self._prepare_shorter_tree(revision=self.revisions[3])
        return retrieve_repository_metadata(str(self.revisions[0]))[0]

    def test_repository_prepared_successfully(self):
        f = open(os.path.join(self.repo, 'test.txt'))
        f1 = f.read()
        f.close()

        f = open(os.path.join(self.repo, 'test2.txt'))
        f2 = f.read()
        f.close()

        self.assertEquals("changed in new_branch again", f1)
        self.assertEquals("changed in master", f2)

    def test_simple_diff_retrieved_both_items(self):
        self._prepare_shorter_tree(self.revisions[4])
        self.assertEquals(2, len(retrieve_repository_metadata(str(self.revisions[0]))))

    def test_simple_diff_retrieved_proper_hashes(self):
        self._prepare_shorter_tree(self.revisions[4])
        
        metadata = retrieve_repository_metadata(str(self.revisions[0]))
        self.assertEquals(self.revisions[3], metadata[0]['hash'])
        self.assertEquals(self.revisions[4], metadata[1]['hash'])

    def test_whole_history_returned_when_no_changeset_provided(self):
        self.assertEquals(6, len(retrieve_repository_metadata(None)))

    def test_simple_diff_contains_author_name(self):
        self.assertEquals('dummy-tester', self._get_metadata_for_revision_4()['author_name'])

    def test_simple_diff_contains_author_email(self):
        self.assertEquals('dummy-tester@example.com', self._get_metadata_for_revision_4()['author_email'])

    def test_simple_diff_contains_commiter_name(self):
        self.assertEquals('dummy-tester', self._get_metadata_for_revision_4()['commiter_name'])

    def test_simple_diff_contains_commiter_email(self):
        self.assertEquals('dummy-tester@example.com', self._get_metadata_for_revision_4()['commiter_email'])

    def test_date_info_is_datetime(self):
        self.assertTrue(isinstance(self._get_metadata_for_revision_4()['commiter_date'], datetime))

    def test_simple_diff_contains_subject(self):
        self.assertEquals('"4"', self._get_metadata_for_revision_4()['subject'])

    def test_whole_history_contains_all_branches(self):
        self.assertEquals(len(self.revisions), len(retrieve_repository_metadata(str(self.revisions[0]))))

    def test_partial_history_contains_another_branch(self):
        self.assertEquals(3, len(retrieve_repository_metadata(str(self.revisions[4]))))
        self.assertEquals([self.revisions[1], self.revisions[2]], [i['hash'] for i in retrieve_repository_metadata(str(self.revisions[4]))[0:2]])


    def test_repository_name_is_part_of_metadata(self):
        # we're assuming origin
        proc = Popen(['git', 'remote', 'add', 'origin', self.repo], stdout=PIPE, stdin=PIPE)
        proc.wait()
        self.assertEquals(0, proc.returncode)

        
        self.assertEquals(self.repo, self._get_metadata_for_revision_4()['repository_uri'])
