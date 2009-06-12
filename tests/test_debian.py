from nose.tools import assert_equals, assert_raises

from citools.debian import ControlParser, Dependency

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
        self.dependencies_list = ["centrum-mypage-icentrum", "centrum-python-mypage", "centrum-djangosherlock-slovniky", "centrum-python-djangosherlock",
            "centrum-mypage-config", "centrum-apache2", "centrum-python-django"]
        self.dependencies_list.sort()

    def test_dependency_list_retrieved_from_file(self):
        
        retrieved = [i.name for i in ControlParser(self.test_control).get_dependencies()]
        retrieved.sort()

        assert_equals(self.dependencies_list, retrieved)
        
    def test_dependency_list_retrieved_from_line(self):
        assert_equals(["centrum-mypage-icentrum", "centrum-python-mypage"],
            [i.name for i in ControlParser(self.test_control).parse_dependency_line("Depends: centrum-mypage-icentrum, centrum-python-mypage (= 0.5.0.0)")]
        )

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

    def test_dependency_merge_version_downgrade_not_allowed(self):
        assert_raises(ValueError, ControlParser(u"").get_dependency_merge,
            current_dependencies = [Dependency(name="mypage", version="0.5.0")],
            new_dependencies = [Dependency(name="mypage", version="0.4.9.9")],
        )

    def test_dependency_merge_multiple_version_in_new_deps_raises_value_error(self):
        assert_raises(ValueError, ControlParser(u"").get_dependency_merge,
            current_dependencies = [Dependency(name="mypage", version="0.5.0")],
            new_dependencies = [Dependency(name="mypage", version="0.4.9.9"), Dependency(name="mypage", version="0.5.0")],
        )
