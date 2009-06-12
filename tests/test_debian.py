import os, os.path
from StringIO import StringIO
from shutil import rmtree
from subprocess import check_call, PIPE
from tempfile import mkdtemp

from nose.tools import assert_equals, assert_raises

from citools.debian import ControlParser, update_dependency_versions, Dependency

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
        self.test_control = """Source: centrum-mypage-meta
Section: apps
Priority: optional
Maintainer: Jan Kral <xxx@xxx.com>
Uploaders: Richard Fridrich <xxx@xxx.com>, Tomas Hrabinsky <xxx@xxx.com>
Build-Depends: cdbs (>= 0.4.41), debhelper (>= 5.0.37.2)
Standards-Version: 3.7.2

# meta package
Package: centrum-mypage-meta
Architecture: all
Depends:
Description: mypage metapackage

# installable frontend metapackage
Package: centrum-mypage-fe
Architecture: all
Depends: centrum-mypage-icentrum (= 0.5.0.0), centrum-python-mypage (= 0.5.0.0), centrum-djangosherlock-slovniky (= 0.2.0.0), centrum-python-djangosherlock (>= 0.0.1), centrum-mypage-config (= 0.5.0.0), centrum-apache2, centrum-python-django
Description: xxx
"""
        self.dependencies_list = [
            "centrum-mypage-icentrum",
            "centrum-python-mypage",
            "centrum-djangosherlock-slovniky",
            "centrum-python-djangosherlock",
            "centrum-mypage-config",
            "centrum-apache2",
            "centrum-python-django"
        ]
        self.dependencies_list.sort()

    def test_dependency_list_retrieved_from_file(self):
        retrieved = [i.name for i in ControlParser(self.test_control).get_dependencies()]
        retrieved.sort()

        assert_equals(self.dependencies_list, retrieved)

    def test_dependency_list_retrieved_from_line(self):
        assert_equals(["centrum-mypage-icentrum", "centrum-python-mypage"],
            [i.name for i in ControlParser(self.test_control).parse_dependency_line("Depends: centrum-mypage-icentrum, centrum-python-mypage (= 0.5.0.0)")]
        )

    def test_dependency_list_retrieved_from_line_with_version(self):
        self.assert_dependencies_equals([Dependency("centrum-python-mypage", "0.5.0.0"), Dependency("centrum-mypage-icentrum")],
            ControlParser(self.test_control).parse_dependency_line("Depends: centrum-mypage-icentrum, centrum-python-mypage (= 0.5.0.0)"),
        )

    def test_depencies_replaced(self):
        self.expected_replaced = u"""Source: centrum-mypage-meta
Section: apps
Priority: optional
Maintainer: Jan Kral <xxx@xxx.com>
Uploaders: Richard Fridrich <xxx@xxx.com>, Tomas Hrabinsky <xxx@xxx.com>
Build-Depends: cdbs (>= 0.4.41), debhelper (>= 5.0.37.2)
Standards-Version: 3.7.2

# meta package
Package: centrum-mypage-meta
Architecture: all
Depends:
Description: mypage metapackage

# installable frontend metapackage
Package: centrum-mypage-fe
Architecture: all
Depends: centrum-mypage-icentrum (= 0.5.0.0), centrum-python-mypage (= 0.5.0.0), centrum-djangosherlock-slovniky (= 0.5.0), centrum-python-djangosherlock (>= 0.0.1), centrum-mypage-config (= 0.5.0.0), centrum-apache2, centrum-python-django
Description: xxx
"""
        parser = ControlParser(self.test_control)
        parser.replace_dependencies(
            dependencies = [Dependency("centrum-djangosherlock-slovniky", "0.5.0")]
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

class TestUpdateDependencyVersions(object):
    def setUp(self):
        self.tmp_control_dir = mkdtemp(prefix='test_control_')
        self.test_control = os.path.join(self.tmp_control_dir, 'control')
        self.control_content = """\
Source: centrum-python-metapackage
Section: python
Priority: optional
Maintainer: John Doe <john@doe.com>
Build-Depends: cdbs (>= 0.4.41), debhelper (>= 5.0.37.2), python-dev, python-support (>= 0.3), python-setuptools
Standards-Version: 3.7.2

Package: centrum-python-metapackage-aaa
Architecture: all
Depends: centrum-python-package1-aaa (= 0.1.0), centrum-python-package2-aaa (= 0.2.0)
Description: metapackage aaa

Package: centrum-python-metapackage-bbb
Architecture: all
Depends: centrum-python-package1-bbb (= 0.1.0), centrum-python-package2-bbb (= 0.2.0)
Description: metapackage bbb

"""

        f = open(self.test_control, 'w')
        f.write(self.control_content)
        f.close()

        self.oldcwd = os.getcwd()

        # create temporary directory and initialize git repository there
        self.package1_name = 'package1'
        self.repo1 = mkdtemp(prefix='test_git1_')
        os.chdir(self.repo1)
        check_call(['git', 'init'], stdout=PIPE, stdin=PIPE)
        open('.gitignore', 'w').close()
        check_call(['git', 'add', '.'], stdout=PIPE, stdin=PIPE)
        check_call(['git', 'commit', '-m', 'initial'], stdout=PIPE, stdin=PIPE)
        check_call(['git', 'tag', '-a', 'project1-0.1', '-m', '"project1 tagged 0.1"'], stdout=PIPE, stdin=PIPE)

        # create debianisation and package in repo
        os.mkdir('debian')
        f = open(os.path.join('debian', 'control'), 'w')
        f.write('''\
Source: centrum-python-package1
Section: python
Priority: optional
Maintainer: John Doe <john@doe.com>
Build-Depends: cdbs (>= 0.4.41), debhelper (>= 5.0.37.2), python-dev, python-support (>= 0.3), python-setuptools
Standards-Version: 3.7.2

Package: centrum-python-package1-aaa
Architecture: all
Depends:
Description: package1

Package: centrum-python-package1-bbb
Architecture: all
Depends:
Description: package1

''')
        f.close()
        check_call(['git', 'add', '.'], stdout=PIPE, stdin=PIPE)
        check_call(['git', 'commit', '-m', 'debianisation added'], stdout=PIPE, stdin=PIPE)

        os.chdir(self.oldcwd)

        # TODO:
        # create function from upper code and create second repository
        # !!! with tag project2-0.2
        self.package2_name = 'package2'
        self.repo2 = mkdtemp(prefix='test_git2_')


    def test_myself(self):
        '''
        os.chdir(self.repo1)
        check_call(['echo', 'AAA',])
        check_call(['git', '--no-pager', 'log', '-p'])
        check_call(['git', 'tag'])
        check_call(['git', 'describe'])
        check_call(['echo', 'BBB',])
        os.chdir(self.oldcwd)
        '''

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
        update_dependency_versions(repositories, self.test_control)

        # TODO: this should not be the same ;)
        control_output = self.control_content

        assert_equals(open(self.test_control).read(), self.control_content)


    def tearDown(self):
        os.chdir(self.oldcwd)

        rmtree(self.tmp_control_dir)
        rmtree(self.repo1)
        rmtree(self.repo2)
