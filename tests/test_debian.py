from StringIO import StringIO
from nose.tools import assert_equals

from citools.debian import ControlParser


class TestControlParsing(object):
    def setUp(self):
        self.test_control = StringIO("""Source: centrum-mypage-meta
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
""")
        self.dependencies_list = ["centrum-mypage-icentrum", "centrum-python-mypage", "centrum-djangosherlock-slovniky", "centrum-python-djangosherlock",
            "centrum-mypage-config", "centrum-apache2", "centrum-python-django"]
        self.dependencies_list.sort()

    def test_dependency_list_retrieved_from_file(self):
        
        retrieved = ControlParser(self.test_control).get_dependencies()
        retrieved.sort()

        assert_equals(self.dependencies_list, retrieved)
        
    def test_dependency_list_retrieved_from_line(self):
        assert_equals(["centrum-mypage-icentrum", "centrum-python-mypage"],
            ControlParser(self.test_control).parse_dependency_line("Depends: centrum-mypage-icentrum, centrum-python-mypage (= 0.5.0.0)")
        )
