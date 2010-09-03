from shutil import rmtree
from tempfile import mkdtemp
from nose.plugins.skip import SkipTest
from subprocess import CalledProcessError
import os
from subprocess import check_call, Popen, PIPE

from helpers import PaverTestCase

class TestPaverVersioning(PaverTestCase):

    def test_version_computes_default(self):
        p = Popen(['paver', '-q', 'compute_version'], stdout=PIPE)
        stdout, stderr = p.communicate()
        self.assertEquals('0.0.1', stdout.strip())

    def test_version_accepts_tag_with_default_pattern(self):
        check_call(['git', 'tag', '-a', 'exproject-2.3', '-m', '"Tagging"'])

        p = Popen(['paver', '-q', 'compute_version'], stdout=PIPE)
        stdout, stderr = p.communicate()
        self.assertEquals('2.3.0', stdout.strip())

    def test_paver_accepts_tag_pattern_as_argument(self):
        check_call(['git', 'tag', '-a', 'wtf-3.3', '-m', '"Tagging"'])

        p = Popen(['paver', '-q', 'compute_version', '--accepted-tag-pattern=wtf-[0-9]*'], stdout=PIPE)
        stdout, stderr = p.communicate()
        self.assertEquals('3.3.0', stdout.strip())

    def test_paver_accepts_tag_pattern_as_argument_in_original_alias(self):
        check_call(['git', 'tag', '-a', 'wtf-3.3', '-m', '"Tagging"'])

        p = Popen(['paver', '-q', 'compute_version_git', '--accepted-tag-pattern=wtf-[0-9]*'], stdout=PIPE)
        stdout, stderr = p.communicate()
        self.assertEquals('3.3.0', stdout.strip())


class DebianPackageTestCase(PaverTestCase):

    def setUp(self):
        super(DebianPackageTestCase, self).setUp()

        try:
            check_call(['dpkg-buildpackage', '--help'], stdout=PIPE, stderr=PIPE)
        except (CalledProcessError, OSError):
            raise SkipTest("This test must run on debian with buildpackage installed")

        check_call(['git', 'tag', '-a', 'exproject-3.3', '-m', '"Tagging"'])

class TestDebianPackaging(DebianPackageTestCase):

    def test_package_creation(self):
        check_call(['paver', '-q', 'replace_version'], stderr=PIPE, stdout=PIPE)
        check_call(['paver', 'create_debian_package'], stderr=PIPE, stdout=PIPE)

        self.assertTrue(os.path.exists(os.path.join(self.repo, os.pardir, "python-exproject_3.3.0_all.deb")))
        self.assertTrue(os.path.exists(os.path.join(self.repo, os.pardir, "python-exproject_3.3.0.dsc")))



class TestFtpUploadFunctions(DebianPackageTestCase):

    def setUp(self):
        super(TestFtpUploadFunctions, self).setUp()

        self.prepare_ftp_server()


    def prepare_ftp_server(self):
        try:
            from pyftpdlib import ftpserver
        except ImportError:
            raise SkipTest("This test requires pyftpdlib to be installed")

        from helpers import FTPd

        self.ftp_home = mkdtemp(prefix='ftp-home-')
        self.username = self.password = "12345"
        self.server = FTPd(user=self.username, passwd=self.password, home=self.ftp_home)
        self.server.start()
        
    def test_ftp_upload(self):
        check_call(['paver', '-q', 'replace_version'], stderr=PIPE, stdout=PIPE)
        check_call(['paver', 'create_debian_package'], stderr=PIPE, stdout=PIPE)
        
        check_call([
            'paver', 'upload_debian_package',
            '--ftp-host=%s' % self.server.host, '--ftp-port=%s' % self.server.port,
            '--ftp-user=%s' % self.username, '--ftp-password=%s' % self.password,
            '--ftp-directory=test/nested/directories'
        ], stderr=PIPE, stdout=PIPE)

        self.assertTrue(os.path.exists(os.path.join(self.ftp_home, "test", "nested", "directories", "python-exproject", "python-exproject_3.3.0_all.deb")))

#    def test_package_creation_accepts_upload(self):
#        check_call([
#            'paver', 'create_debian_package',
#            '--upload-ftp',
#            '--ftp-host=%s' % self.server.host, '--ftp-port=%s' % self.server.port,
#            '--ftp-user=%s' % self.username, '--ftp-password=%s' % self.password,
#            '--ftp-directory=test/nested/directories'
#        ])
#
#        self.assertTrue(os.path.exists(os.path.join(self.ftp_home, "test", "nested", "directories", "python-exproject", "python-exproject_3.3.0_all.deb")))

    def tearDown(self):
        self.server.stop()
        rmtree(self.ftp_home)

        super(TestFtpUploadFunctions, self).tearDown()

