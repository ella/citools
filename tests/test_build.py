import os
from shutil import rmtree
from subprocess import check_call, PIPE
from tempfile import mkdtemp

from nose.tools import assert_equals

from citools.build import copy_images

class TestCopyImages(object):

    def setUp(self):
        
        # create temporary directory and initialize git repository there
        self.repo = mkdtemp(prefix='test_git_')
        self.tmp_static = mkdtemp(prefix='test_static_')
        self.oldcwd = os.getcwd()
        os.chdir(self.repo)
        check_call(['git', 'init'], stdout=PIPE, stdin=PIPE)


        # create default "package layout"
        self.package_name = 'mypackage'

        os.mkdir(self.package_name)
        os.mkdir(os.path.join(self.package_name, 'static'))
        os.mkdir(os.path.join(self.package_name, 'static', 'images'))
        self.filename = os.path.join(self.package_name, 'static', 'images', 'test.txt')

        self.file_content = 'WTFFILE!!!'

        f = open(self.filename, 'w')
        f.write(self.file_content)
        f.close()

        check_call(['git', 'add', self.filename], stdout=PIPE, stdin=PIPE)
        check_call(['git', 'commit', '-a', '-m', '"Adding test"'], stdout=PIPE, stdin=PIPE)

    def test_images_copied_on_right_place(self):
        copy_images(repositories=[{
            'url': os.path.abspath(self.repo),
            'branch': 'master',
            'package_name' : self.package_name,
        }], static_dir=self.tmp_static)

        assert_equals(self.file_content, open(os.path.join(self.tmp_static, self.package_name, 'images', 'test.txt')).read())

    def tearDown(self):
        os.chdir(self.oldcwd)

        rmtree(self.repo)
        rmtree(self.tmp_static)

