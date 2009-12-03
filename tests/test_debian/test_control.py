from nose.tools import assert_equals, assert_raises, assert_true

from citools.debian.control import ControlFileParagraph, SourceParagraph, \
    Dependency, ControlFile, PackageParagraph

# {{{  Test ControlFileParagraph generic parsing
##############################################################################

def test_multiline_values_work():
    source = 'key1: value1\nkey2: value\n on more\n lines'
    par = ControlFileParagraph(source)
    assert_equals('value on more lines', par.key2)

def test_custom_parsing_hooks_get_fired():
    class MyControlFileParagraph(ControlFileParagraph):
        def parse_my_key(self, value):
            return 'X%sX' % value
    source = 'key1: value1\nMy-Key: my custom value'
    par = MyControlFileParagraph(source)
    assert_equals('Xmy custom valueX', par.my_key)
    assert_equals('value1', par.key1)

def test_defining_params():
    par = ControlFileParagraph('')
    assert_raises(AttributeError, getattr, par, 'xx')
    par.xx = 12
    assert_equals(12, par.xx)

def test_dumping_works():
    par = ControlFileParagraph('')
    par.xx = "12"
    par.xy = "42"
    assert_equals('xx: 12\nxy: 42', par.dump())

def test_custom_dump_hooks():
    class MyControlFileParagraph(ControlFileParagraph):
        def dump_mykey(self, value):
            return 'XX'.join(value)
    par = MyControlFileParagraph('')
    par.xx = "12"
    par.mykey = ['a', 'b', 'c']
    assert_equals('xx: 12\nmykey: aXXbXXc', par.dump())

def test_basic_sanity():
    source = 'key1: value1\nMy-Key: value2'
    par = ControlFileParagraph(source)
    assert_equals(source, par.dump())

##############################################################################
# }}}


# {{{  Test PackageParagraph
##############################################################################

def test_package_parses_versioned_package():
    package = 'python-django-1.1'
    parsed = PackageParagraph('').parse_package(package)
    assert_equals('python-django', parsed.name)
    assert_equals('1.1', parsed.version)
    assert_equals(True, parsed.is_versioned())

def test_dependency_parses_version_info():
    package = 'python-django (>= 1.1)'
    parsed = PackageParagraph('').parse_depends(package)
    assert_equals(1, len(parsed))
    dep = parsed[0]
    assert_equals('>=', dep.sign)
    assert_equals('python-django', dep.name)
    assert_equals('1.1', dep.version)

def test_dependency_parses_versioned_packages():
    package = 'python-django-1.1, ella (1.32)'
    parsed = PackageParagraph('').parse_depends(package)
    assert_equals(2, len(parsed))

    dep = parsed[0]
    assert_equals('', dep.sign)
    assert_equals('python-django', dep.name)
    assert_equals('1.1', dep.version)

    dep = parsed[1]
    assert_equals('=', dep.sign)
    assert_equals('ella', dep.name)
    assert_equals('1.32', dep.version)


def test_dependency_parses_packages_with_signs():
    package = 'centrum-python-package1-aaa (= 0.1.0), centrum-python-package2-aaa (= 0.2.1)'
    parsed = PackageParagraph('').parse_depends(package)
    assert_equals(2, len(parsed))

    dep = parsed[0]
    assert_equals('=', dep.sign)
    assert_equals('centrum-python-package1-aaa', dep.name)
    assert_equals('0.1.0', dep.version)

    dep = parsed[1]
    assert_equals('=', dep.sign)
    assert_equals('centrum-python-package2-aaa', dep.name)
    assert_equals('0.2.1', dep.version)

def test_dependency_parses_versioned_package():
    package = 'python-django-1.1'
    parsed = PackageParagraph('').parse_depends(package)
    assert_equals(1, len(parsed))
    dep = parsed[0]
    assert_equals('', dep.sign)
    assert_equals('python-django', dep.name)
    assert_equals('1.1', dep.version)

def test_package_pargraph_deals_with_empty_depends():
    package = '''\
Package: package-with-static-files-%(version)s
Architecture: all
Depends:
Description: package with static files with versioned path
'''
    parsed = PackageParagraph(package)

##############################################################################
# }}}


# {{{  Test Dependency
##############################################################################

def test_dependency_without_version_doesnt_print_one():
    d = Dependency('ella')
    assert_equals('ella', str(d))

def test_dependency_without_sign_is_versioned_package():
    d = Dependency('ella', '1.0')
    assert_equals('ella-1.0', str(d))

def test_dependency_with_sign_prints_correctly():
    d = Dependency('ella', '1.0', '=')
    assert_equals('ella (= 1.0)', str(d))

def test_dependency_with_sign_is_not_versioned():
    d = Dependency('ella', '1.0', '=')
    assert_equals(False, d.is_versioned())

def test_dependency_without_sign_is_versioned():
    d = Dependency('ella', '1.0')
    assert_equals(True, d.is_versioned())

##############################################################################
# }}}


# {{{  Test ControlFile
##############################################################################

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

def test_empty_source_to_control_file_creates_source_paragraph():
    cf = ControlFile()
    assert isinstance(cf.source, SourceParagraph)
    assert_equals(0, len(cf.packages))

def test_dependencies_get_collected_from_all_packages():
    cfile = master_control_content_pattern % {
        'package1_name': 'package1',
        'package2_name': 'package2',
        'package1_version': '0.1.0',
        'package2_version': '0.2.1',
        'metapackage_version': '0.10.0',
    }
    cf = ControlFile(cfile)
    assert_equals(
        [
            'centrum-python-package1-aaa (= 0.1.0)',
            'centrum-python-package2-aaa (= 0.2.1)',
            'centrum-python-package1-bbb (= 0.1.0)',
            'centrum-python-package2-bbb (= 0.2.1)',
            'centrum-python-metapackage-aaa (= 0.10.0)'
        ],
        [ str(d) for d in cf.get_dependencies()]
    )

def test_control_file_dump():
    cfile = master_control_content_pattern % {
        'package1_name': 'package1',
        'package2_name': 'package2',
        'package1_version': '0.1.0',
        'package2_version': '0.2.1',
        'metapackage_version': '0.10.0',
    }
    cf = ControlFile(cfile)
    assert_equals(cfile.strip(), cf.dump())

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

def test_control_file_dump2():
    dc = debian_control % {'version': '0.0.0.0'}
    cfile = ControlFile(dc)
    assert_equals([l.strip() for l in dc.splitlines()], [l.strip() for l in cfile.dump().splitlines()])

##############################################################################
# }}}

