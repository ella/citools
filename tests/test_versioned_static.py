
import os
from os.path import join
from shutil import rmtree
from tempfile import mkdtemp

from nose.tools import assert_equals


debian_control = '''\
Source: package-with-static-files
Section: python
Priority: optional
Maintainer: John Doe <john@doe.com>
Build-Depends: cdbs (>= 0.4.41), debhelper (>= 5.0.37.2), python-dev, python-support (>= 0.3), python-setuptools
Standards-Version: 3.7.2

Package: package-with-static-files
Architecture: all
Depends: package-with-static-files-%(version)s
Description: package with static files without version in path

Package: package-with-static-files-%(version)s
Architecture: all
Depends:
Description: package with static files with versioned path
'''

debian_package_dirs = 'var/www/package'
debian_package_install = 'data/* var/www/package'
debian_package_version_dirs = 'var/www/package/%(version)s'
debian_package_version_install = 'data/* var/www/package/%(version)s'

TEST_DIR_STRUCTURE = (
    (join('.'), None),
    (join('.', 'debian'), None),
    (join('.', 'debian', 'control'), debian_control % {'version': 'VERSION',}),
    (join('.', 'debian', 'package-with-static-files.dirs'), debian_package_dirs),
    (join('.', 'debian', 'package-with-static-files.install'), debian_package_install),
    (join('.', 'debian', 'package-with-static-files-VERSION.dirs'), debian_package_version_dirs % {'version': 'VERSION',}),
    (join('.', 'debian', 'package-with-static-files-VERSION.install'), debian_package_version_install % {'version': 'VERSION',}),
)


class TestVersionedStatic(object):
    def setUp(self):
        self.oldcwd = os.getcwd()
        self.directory = mkdtemp(prefix='test_versioned_static_')
        os.chdir(self.directory)
        self.create_structure_from_variable(TEST_DIR_STRUCTURE)

    def create_structure_from_variable(self, dir_structure):
        '''
        create directory structure via given list of tuples (filename, content,)
        content being None means it is directory
        '''
        for filename, content in dir_structure:
            if content is None:
                try:
                    os.makedirs(filename)
                except OSError:
                    pass
            else:
                f = open(filename, 'w')
                f.write(content)
                f.close()

    def store_directory_structure(self, path):
        '''
        recursivelly traverse directory and store it in format
        that can be given to create_structure_from_variable()
        '''
        d = {}
        for base, dirs, files in os.walk(path):
            d[base] = None
            for i in files:
                fn = join(base, i)
                f = open(fn, 'r')
                d[fn] = f.read()
                f.close()
        return d.items()

    def test_all_version_occurences_are_replaced(self):
        '''
        list resulting directory and compare with expected result
        '''

        # TODO: call functionality :))

        actual_structure = sorted(self.store_directory_structure('.'))
        expected_structure = sorted((
            (join('.'), None),
            (join('.', 'debian'), None),
            (join('.', 'debian', 'control'), debian_control % {'version': '1.2.3',}),
            (join('.', 'debian', 'package-with-static-files.dirs'), debian_package_dirs),
            (join('.', 'debian', 'package-with-static-files.install'), debian_package_install),
            (join('.', 'debian', 'package-with-static-files-1.2.3.dirs'), debian_package_version_dirs % {'version': '1.2.3',}),
            (join('.', 'debian', 'package-with-static-files-1.2.3.install'), debian_package_version_install % {'version': '1.2.3',}),
        ))

        for actual, expected in zip(actual_structure, expected_structure):
            assert_equals(actual, expected)

    def tearDown(self):
        os.chdir(self.oldcwd)
        rmtree(self.directory)

