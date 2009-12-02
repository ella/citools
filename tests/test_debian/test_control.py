from nose.tools import assert_equals, assert_raises, assert_true

from citools.debian.control import ControlFileParagraph, SourceParagraph, \
    Dependency

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


# {{{  Test SourceParagraph
##############################################################################

def test_dependency_parses_version_info():
    package = 'python-django (=> 1.1)'
    parsed = SourceParagraph('').parse_depends(package)
    assert_equals(1, len(parsed))
    dep = parsed[0]
    assert_equals('=>', dep.sign)
    assert_equals('python-django', dep.name)
    assert_equals('1.1', dep.version)

def test_dependency_parses_versioned_package():
    package = 'python-django-1.1, ella (1.32)'
    parsed = SourceParagraph('').parse_depends(package)
    assert_equals(2, len(parsed))

    dep = parsed[0]
    assert_equals('', dep.sign)
    assert_equals('python-django', dep.name)
    assert_equals('1.1', dep.version)

    dep = parsed[1]
    assert_equals('=', dep.sign)
    assert_equals('ella', dep.name)
    assert_equals('1.32', dep.version)

def test_dependency_parses_versioned_package():
    package = 'python-django-1.1'
    parsed = SourceParagraph('').parse_depends(package)
    assert_equals(1, len(parsed))
    dep = parsed[0]
    assert_equals('', dep.sign)
    assert_equals('python-django', dep.name)
    assert_equals('1.1', dep.version)

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

##############################################################################
# }}}

