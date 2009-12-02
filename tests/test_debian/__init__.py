import os
from os.path import join
from shutil import rmtree
from subprocess import check_call, PIPE
from tempfile import mkdtemp

from nose.tools import assert_equals, assert_raises, assert_true

from citools.debian.commands import (
    ControlParser, update_dependency_versions, Dependency,
    VersionedDependency, replace_versioned_packages,
    replace_versioned_debian_files,
)


master_control_content_pattern = u"""\
Source: centrum-python-metapackage
Section: python
Priority: optional
Maintainer: John Doe <john@doe.com>
Build-Depends: cdbs (>= 0.4.41), debhelper (>= 5.0.37.2), python-dev, python-support (>= 0.3), python-setuptools
Standards-Version: 3.7.2

Package: centrum-python-metapackage-aaa
Architecture: all
Depends: centrum-python-%(package1_name)s-aaa (= %(package1_version)s), centrum-python-%(package2_name)s-aaa (= %(package2_version)s)
Description: metapackage aaa

Package: centrum-python-metapackage-bbb
Architecture: all
Depends: centrum-python-%(package1_name)s-bbb (= %(package1_version)s), centrum-python-%(package2_name)s-bbb (= %(package2_version)s), centrum-python-metapackage-aaa (= %(metapackage_version)s)
Description: metapackage bbb

Package: centrum-python-metapackage-aaa-static-files-0.0.0
Architecture: all
Description: static files for metapackage
"""

slave_control_content_pattern = u"""\
Source: centrum-python-%(project_name)s
Section: python
Priority: optional
Maintainer: John Doe <john@doe.com>
Build-Depends: cdbs (>= 0.4.41), debhelper (>= 5.0.37.2), python-dev, python-support (>= 0.3), python-setuptools
Standards-Version: 3.7.2

Package: centrum-python-%(project_name)s-aaa
Architecture: all
Depends:
Description: %(project_name)s aaa

Package: centrum-python-%(project_name)s-bbb
Architecture: all
Depends:
Description: %(project_name)s bbb
"""


class DependencyTestCase(object):
    def assert_dependencies_equals(self, expect, retrieved):
        """
        Dependencies are considered equal if every entry in expect has
        dependency entry in retrieved, that has same name and version
        """
        unmatched = []
        for dep in expect:
            matches = [i for i in retrieved if i.name == dep.name and i.version == dep.version]
            if len(matches) < 1:
                unmatched.append(str(dep))
        if len(unmatched) > 0:
            raise AssertionError("Expected dependencies %s not found in retrieved deps %s" % (
                str(unmatched),
                str([str(i) for i in retrieved])
            ))

class TestControlParsing(DependencyTestCase):
    def setUp(self):
        self.test_control= master_control_content_pattern % {
            'package1_name': 'package1',
            'package2_name': 'package2',
            'package1_version': '0.1.0',
            'package2_version': '0.2.0',
            'metapackage_version': '0.10.0',
        }

        self.dependencies_list = [
            "centrum-python-package1-aaa",
            "centrum-python-package2-aaa",
            "centrum-python-package1-bbb",
            "centrum-python-package2-bbb",
            "centrum-python-metapackage-aaa",
        ]
        self.dependencies_list.sort()

    def test_dependency_list_retrieved_from_file(self):
        retrieved = [i.name for i in ControlParser(self.test_control).get_dependencies()]
        retrieved.sort()

        assert_equals(self.dependencies_list, retrieved)

    def test_dependency_list_retrieved_from_line(self):
        assert_equals(["centrum-python-package1-aaa", "centrum-python-package2-aaa"],
            [i.name for i in ControlParser(self.test_control).parse_dependency_line("Depends: centrum-python-package1-aaa, centrum-python-package2-aaa (= 0.2.0)")]
        )

    def test_dependency_list_retrieved_from_line_with_version(self):
        self.assert_dependencies_equals([Dependency("centrum-python-package2-aaa", "0.2.0"), Dependency("centrum-python-package1-aaa")],
            ControlParser(self.test_control).parse_dependency_line("Depends: centrum-python-package1-aaa, centrum-python-package2-aaa (= 0.2.0)"),
        )

    def test_dependency_list_retrieved_for_versioned_package(self):
        self.assert_dependencies_equals([VersionedDependency(name="package-static", version="0.5.5"), Dependency(name="package-static")],
            ControlParser(self.test_control).parse_dependency_line("Depends: package-static, package-static-0.5.5"),
        )

    def test_versioned_package_name_recognized(self):
        assert_equals("package2-with-static-files",
            ControlParser(self.test_control).parse_package_line("Package: package2-with-static-files-0.3.25")[0].name
        )

    def test_versioned_package_name_version_recognized(self):
        assert_equals("0.3.25",
            ControlParser(self.test_control).parse_package_line("Package: package-with-static-files-0.3.25")[0].version
        )

    def test_versioned_package_name_replaced(self):
        parser = ControlParser("Package: package-with-static-files-0.5.0")
        parser.replace_versioned_packages(version="1.5.78")

        assert_equals("Package: package-with-static-files-1.5.78", parser.control_file.strip())

        

    def test_depencies_replaced(self):
        self.expected_replaced = master_control_content_pattern % {
            'package1_name': 'package1',
            'package2_name': 'package2',
            'package1_version': '0.1.0',
            'package2_version': '0.2.1',
            'metapackage_version': '0.10.0',
        }

        parser = ControlParser(self.test_control)
        parser.replace_dependencies(
            dependencies = [Dependency("centrum-python-package2-aaa", "0.2.1"), Dependency("centrum-python-package2-bbb", "0.2.1"),]
        )

        assert_equals(self.expected_replaced, parser.control_file)

    def test_debversion_parsing_simple(self):
        dep = Dependency(u"")
        dep.extract_version_from_debversion(" (= 0.5.0.0)")
        assert_equals("0.5.0.0",  dep.version)

    def test_debversion_parsing_with_noneqaual_signs(self):
        dep = Dependency(u"")
        dep.extract_version_from_debversion(" (>= 0.1)")
        assert_equals(">=",  dep.sign)
        # sanity check
        assert_equals("0.1",  dep.version)

    def test_packages_retrieved(self):
        parser = ControlParser(self.test_control)
        packages = [u'centrum-python-metapackage-aaa', u'centrum-python-metapackage-bbb', 'centrum-python-metapackage-aaa-static-files']

        assert_equals(packages, [p.name for p in parser.get_packages()])

    def test_upgrade_to_multicipher_version_passes_downgrade_check(self):
        parser = ControlParser(self.test_control)
        assert_true(parser.check_downgrade('0.5.0.0', '0.17.0.114'))


class TestDependency(DependencyTestCase):
        
    def test_dependency_string_without_version(self):
        assert_equals('centrum-mypage', Dependency(name='centrum-mypage').get_dependency_string())

    def test_dependency_string_with_version(self):
        assert_equals('centrum-mypage (= 0.5.0.0)', Dependency(name='centrum-mypage', version='0.5.0.0').get_dependency_string())

    def test_dependency_merge_version(self):
        expected_dependencies = [
                Dependency("mypage", "0.6.1"),
                Dependency(name="python"),
                Dependency("mypage-config", "0.6.1"),
            ]
        current_dependencies = [
            Dependency(name="mypage", version="0.5.0"),
            Dependency(name="python"),
            Dependency("mypage-config", "0.6.1"),
        ]
        new_dependencies = [
            Dependency(name="mypage", version="0.6.1"),
            Dependency(name="python", version="2.6.2"),
            Dependency(name="iwhatever", version="0.5.0")
        ]
        self.assert_dependencies_equals(expected_dependencies, ControlParser(u"").get_dependency_merge(
            current_dependencies = current_dependencies,
            new_dependencies = new_dependencies,
        ))

    def test_dependency_merge_version_nonequals_not_merged(self):
        expected_dependencies = [
                Dependency("mypage", "0.5.0"),
            ]
        current_dependencies = [
            Dependency(name="mypage", version="0.5.0", sign=">="),
        ]
        new_dependencies = [
            Dependency(name="mypage", version="0.6.1"),
        ]
        self.assert_dependencies_equals(expected_dependencies, ControlParser(u"").get_dependency_merge(
            current_dependencies = current_dependencies,
            new_dependencies = new_dependencies,
        ))

    def test_dependency_merge_version_downgrade_not_allowed(self):
        assert_raises(ValueError, ControlParser(u"").get_dependency_merge,
            current_dependencies = [Dependency(name="mypage", version="0.5.0")],
            new_dependencies = [Dependency(name="mypage", version="0.4.9.9")],
        )

    def test_dependency_merge_version_downgrade_not_allowed_with_first_version_longer_than_second(self):
        assert_raises(ValueError, ControlParser(u"").get_dependency_merge,
            current_dependencies = [Dependency(name="mypage", version="0.4.9.9.9")],
            new_dependencies = [Dependency(name="mypage", version="0.4.9.9")],
        )

    def test_dependency_merge_version_downgrade_allowed_with_first_version_longer_but_lower_than_second(self):
        self.assert_dependencies_equals([Dependency(name="mypage", version="0.4.9")], ControlParser(u"").get_dependency_merge(
            current_dependencies = [Dependency(name="mypage", version="0.3.9.8")],
            new_dependencies = [Dependency(name="mypage", version="0.4.9")],
        ))

    def test_dependency_merge_multiple_version_in_new_deps_raises_value_error(self):
        assert_raises(ValueError, ControlParser(u"").get_dependency_merge,
            current_dependencies = [Dependency(name="mypage", version="0.5.0")],
            new_dependencies = [Dependency(name="mypage", version="0.4.9.9"), Dependency(name="mypage", version="0.5.0")],
        )

    def test_dependency_merge_versioned_and_nonversioned_allowed(self):
        expected_dependencies = [
            Dependency(name="static", version="1.0.0"),
            VersionedDependency(name="static"),
        ]
        current_dependencies = [
            Dependency(name="static", version="0.5.0"),
            VersionedDependency(name="static"),
        ]
        new_dependencies = [
            VersionedDependency(name="static", version="1.0.0"),
        ]
        self.assert_dependencies_equals(expected_dependencies, ControlParser(u"").get_dependency_merge(
            current_dependencies = current_dependencies,
            new_dependencies = new_dependencies,
        ))

class TestUpdateDependencyVersions(object):
    def setUp(self):
        self.oldcwd = os.getcwd()

        # create temporary directory and initialize git repository there
        self.package1_name = 'package1'
        self.repo1 = mkdtemp(prefix='test_git1_')
        self.create_repository(self.repo1, self.package1_name, '0.1')

        # and another one
        self.package2_name = 'package2'
        self.repo2 = mkdtemp(prefix='test_git2_')
        self.create_repository(self.repo2, self.package2_name, '0.2')

        # create meta repository
        self.metapackage_name = 'metapackage'
        self.metarepo = mkdtemp(prefix='test_git_meta_')
        self.create_repository(self.metarepo, self.metapackage_name, '0.10')

        # create testing control file
        self.test_control = os.path.join(self.metarepo, 'debian', 'control')
        self.control_content = master_control_content_pattern % {
            'package1_name': self.package1_name,
            'package2_name': self.package2_name,
            'package1_version': '0.1.0',
            'package2_version': '0.2.0',
            'metapackage_version': '0.10.0',
        }
        f = open(self.test_control, 'w')
        f.write(self.control_content)
        f.close()

        # and commit new control file
        os.chdir(self.metarepo)
        check_call(['git', 'add', '.'], stdout=PIPE, stdin=PIPE)
        check_call(['git', 'commit', '-m', 'meta control file'], stdout=PIPE, stdin=PIPE)
        os.chdir(self.oldcwd)

    def create_repository(self, repository_dir, project_name, tag_number):
        os.chdir(repository_dir)

        check_call(['git', 'init'], stdout=PIPE, stdin=PIPE)

        # initial commit
        open('.gitignore', 'w').close()

        check_call(['git', 'add', '.'], stdout=PIPE, stdin=PIPE)
        check_call(['git', 'commit', '-m', 'initial'], stdout=PIPE, stdin=PIPE)

        # tag it
        tag_name = '%s-%s' % (project_name, tag_number)
        tag_message = '"%s tagged %s"' % (project_name, tag_number)
        check_call(['git', 'tag', '-a', tag_number, '-m', tag_message], stdout=PIPE, stdin=PIPE)

        # create debianisation and package in repo
        os.mkdir('debian')
        f = open(os.path.join('debian', 'control'), 'w')
        f.write(slave_control_content_pattern % {'project_name': project_name,})
        f.close()

        check_call(['git', 'add', '.'], stdout=PIPE, stdin=PIPE)
        check_call(['git', 'commit', '-m', 'debianisation added'], stdout=PIPE, stdin=PIPE)

        os.chdir(self.oldcwd)


    def test_dependencies_versions_correctly_replaced(self):
        repositories = [
            {
                'url': self.repo1,
                'branch': 'master',
                'package_name': self.package1_name,
            },
            {
                'url': self.repo2,
                'branch': 'master',
                'package_name': self.package2_name,
            },
        ]

        update_dependency_versions(repositories, self.test_control, workdir=self.metarepo)

        expected_control_output = master_control_content_pattern % {
            'package1_name': self.package1_name,
            'package2_name': self.package2_name,
            'package1_version': '0.1.1',
            'package2_version': '0.2.1',
            'metapackage_version': '0.13.4',
        }

        assert_equals(expected_control_output, open(self.test_control).read())


    def tearDown(self):
        os.chdir(self.oldcwd)

        rmtree(self.repo1)
        rmtree(self.repo2)
        rmtree(self.metarepo)


class TestVersionedStatic(object):
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
        (join('.', 'debian', 'control'), debian_control % {'version': '0.0.0.0',}),
        (join('.', 'debian', 'package-with-static-files.dirs'), debian_package_dirs),
        (join('.', 'debian', 'package-with-static-files.install'), debian_package_install),
        (join('.', 'debian', 'package-with-static-files-0.0.0.0.dirs'), debian_package_version_dirs % {'version': '0.0.0.0',}),
        (join('.', 'debian', 'package-with-static-files-0.0.0.0.install'), debian_package_version_install % {'version': '0.0.0.0',}),
    )


    def setUp(self):
        self.oldcwd = os.getcwd()
        self.directory = mkdtemp(prefix='test_versioned_static_')
        os.chdir(self.directory)
        self.create_structure_from_variable(self.TEST_DIR_STRUCTURE)

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
        version = '1.2.3'
        original_version = '0.0.0.0'

        control_path = join(self.directory, 'debian', 'control')
        replace_versioned_debian_files(debian_path=join(self.directory, 'debian'), original_version=original_version, new_version=version)
        replace_versioned_packages(control_path=control_path, version=version)


        actual_structure = sorted(self.store_directory_structure('.'))
        expected_structure = sorted((
            (join('.'), None),
            (join('.', 'debian'), None),
            (join('.', 'debian', 'control'), self.debian_control % {'version': version,}),
            (join('.', 'debian', 'package-with-static-files.dirs'), self.debian_package_dirs),
            (join('.', 'debian', 'package-with-static-files.install'), self.debian_package_install),
            (join('.', 'debian', 'package-with-static-files-1.2.3.dirs'), self.debian_package_version_dirs % {'version': version,}),
            (join('.', 'debian', 'package-with-static-files-1.2.3.install'), self.debian_package_version_install % {'version': version,}),
        ))

        actual_structure_filenames = [ f for f, c in actual_structure ]
        actual_structure_contents  = [ c for f, c in actual_structure ]
        expected_structure_filenames = [ f for f, c in expected_structure ]
        expected_structure_contents  = [ c for f, c in expected_structure ]

        # guard assertion
        assert_equals(expected_structure_filenames, actual_structure_filenames)
        assert_equals(expected_structure_contents, actual_structure_contents)

        for (exp_fname, exp_content), (act_fname, act_content) in zip(expected_structure, actual_structure):
            assert_equals(exp_fname, act_fname) # test file name
            assert_equals(exp_content, act_content) # test file content

    def tearDown(self):
        os.chdir(self.oldcwd)
        rmtree(self.directory)

