import os
from shutil import rmtree
from subprocess import check_call, PIPE
from tempfile import mkdtemp

from nose.tools import assert_equals, assert_true

from citools.build import copy_images, replace_template_files, replace_template_filenames

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

    def test_dependency_without_static_is_ommited(self):
        # create temporary directory and initialize git repository there
        tmp_repo = mkdtemp(prefix='test_git_', dir=self.repo)
        check_call(['git', 'init'], stdout=PIPE, stdin=PIPE, cwd=tmp_repo)

        # commit something empty
        f = open(os.path.join(tmp_repo, 'testicek.txt'), 'w')
        f.write(self.file_content)
        f.close()

        check_call(['git', 'add', os.path.join(tmp_repo, 'testicek.txt')], stdout=PIPE, stdin=PIPE, cwd=tmp_repo)
        check_call(['git', 'commit', '-a', '-m', '"Dummy test"'], stdout=PIPE, stdin=PIPE, cwd=tmp_repo)


        copy_images(repositories=[{
            'url': os.path.abspath(tmp_repo),
            'branch': 'master',
            'package_name' : self.package_name,
        },
        {
            'url': os.path.abspath(self.repo),
            'branch': 'master',
            'package_name' : self.package_name,
        }], static_dir=self.tmp_static)

        # sanity test: while we copied without error, second repo was OK
        assert_equals(self.file_content, open(os.path.join(self.tmp_static, self.package_name, 'images', 'test.txt')).read())


    def tearDown(self):
        os.chdir(self.oldcwd)

        rmtree(self.repo)
        rmtree(self.tmp_static)

class TestTemplateReplacement(object):
    def setUp(self):
        self.tmp = mkdtemp('test-build-')
        
        self.oldcwd = os.getcwd()
        os.chdir(self.tmp)
        
    def test_simple_replacing_inside_file(self):
        req = "dependency-{{ branch }}"
        req_fn = os.path.join(self.tmp, 'requirements.txt') 
        
        f = open(req_fn, 'w')
        f.write(req)
        f.close()        
        
        replace_template_files(root_directory=self.tmp, variables={
            'branch' : 'test',
        })
        
        assert_equals("dependency-test", open(req_fn).read())

    def test_filename_replacement(self):
        req = "Example debian postinstall file"
        req_fn = os.path.join(self.tmp, 'debian-postinstal-for-package-branch-{{ branch }}.postinstall') 
        
        f = open(req_fn, 'w')
        f.write(req)
        f.close()        
        
        replace_template_filenames(root_directory=self.tmp, variables={
            'branch' : 'auto',
        }, subdirs=["."])
        
        fn = os.path.join(self.tmp, 'debian-postinstal-for-package-branch-auto.postinstall')
        assert_true(os.path.exists(fn), "%s not in %s" % (str(fn), os.listdir(self.tmp)))
        

    def tearDown(self):
        os.chdir(self.oldcwd)

        rmtree(self.tmp)
