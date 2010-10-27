from operator import or_
from pyparsing import (
        ParserElement, LineEnd, CharsNotIn, Group, Word,
        alphanums, Literal, Combine, ZeroOrMore, nums,
        Optional, delimitedList, restOfLine
    )
from itertools import chain

class ControlFileParagraph(dict):
    def __init__(self, source):
        self._keys = []
        self._parse(source)
        super(ControlFileParagraph, self).__init__()

    def _parse_items(self, source):
        ParserElement.setDefaultWhitespaceChars(' \t\r')
        EOL = LineEnd().suppress()
        comment = Literal('#') + Optional( restOfLine ) + EOL
        string = CharsNotIn("\n")
        line = Group(
            Word(alphanums + '-')('key') + Literal(':').suppress() + Optional(Combine(string + ZeroOrMore(EOL + Literal(' ') + string)))("value") + EOL
        )
        group = ZeroOrMore(line)
        group.ignore(comment)
        return group.parseString(source, True)

    def _att_key(self, key):
        return key.lower().replace('-', '_')

    def _parse(self, source):
        for row in self._parse_items(source):
            key, value = row.key, row.value
            att_key = self._att_key(key)
            if hasattr(self, 'parse_%s' % att_key):
                value = getattr(self, 'parse_%s' % att_key)(value)

            self[key] = value

    def dump(self):
        out = []
        for key in self._keys:
            att_key = self._att_key(key)
            value = self[att_key]
            if hasattr(self, 'dump_%s' % att_key):
                value = getattr(self, 'dump_%s' % att_key)(value)

            out.append('%s: %s' % (key, value))
        return '\n'.join(out)
    __str__ = dump

    def __repr__(self):
        try:
            return '<ControlFileParagraph: %s>' % self
        except:
            return '<ControlFileParagraph: %r>' % super(ControlFileParagraph, self).__repr__()

    def __getitem__(self, name):
        att_key = self._att_key(name)
        return super(ControlFileParagraph, self).__getitem__(att_key)

    def __setitem__(self, name, value):
        att_key = self._att_key(name)
        if att_key in self:
            super(ControlFileParagraph, self).__setitem__(att_key, value)
        else:
            self._keys.append(name)
            super(ControlFileParagraph, self).__setitem__(att_key, value)

class Dependency(object):
    def __init__(self, name, version='', sign=''):
        self.name, self.version, self.sign = name, version, sign

    def __str__(self):
        if self.sign:
            return '%s (%s %s)' % (self.name, self.sign, self.version)
        else:
            if self.version:
                return '%s-%s' % (self.name, self.version)
        return self.name

    def __repr__(self):
        return '<Dependency(%r, %r, %r)>' % (self.name, self.version, self.sign)

    def is_versioned(self):
        return bool(self.version and not self.sign)

def get_dependency(name, sign='', version=''):
    if version and not sign:
        sign = '='

    if not version:
        package_name = name.rstrip(nums + '.-')
        if package_name != name:
            version_candidate = name[len(package_name):]
            if version_candidate[0] == '-':
                version = version_candidate[1:]
                name = package_name
    return Dependency(name, version, sign)

class SourceParagraph(ControlFileParagraph):
    pass

class PackageParagraph(ControlFileParagraph):
    def parse_package(self, value):
        return get_dependency(value)

    def parse_depends(self, value):
        package_name = Word(alphanums + '.-${}:')('name')
        version = Word(nums + '.-')('version')
        sign = reduce(or_, map(Literal, ('>=', '<=', '=',)))('sign')
        dependency = (
                (
                    package_name +
                    Literal('(').suppress() +
                    Optional(sign)('sign') +
                    version +
                    Literal(')').suppress()
                ) | (
                    package_name
                )
            ).setParseAction(lambda x: get_dependency(x.name, x.sign, x.version))
        dependencies = Optional(delimitedList(dependency, ','))
        return dependencies.parseString(value, True).asList()

    def dump_depends(self, value):
        return ', '.join(map(str, value))

class ControlFile(object):
    DEFAULT_SOURCE_PARAGRAPH = """Section: python
Priority: optional
Build-Depends: cdbs (>= 0.4.41), debhelper (>= 5.0.37.2), python-dev, python-support (>= 0.3), python-setuptools
Standards-Version: 3.7.2
"""

    DEFAULT_PACKAGE_PARAGRAPH = """Architecture: all
Depends: python (>= 2.5.0)
"""

    def __init__(self, source=None, filename=''):
        if filename:
            f = open(filename)
            source = f.read()
            f.close

        if source:
            paragraphs = source.split('\n\n')
        else:
            paragraphs = [self.DEFAULT_SOURCE_PARAGRAPH]

        if not paragraphs:
            # FIXME - add some exception
            raise NotImplementedError()
        self.source = SourceParagraph(paragraphs[0])
        self.packages = []
        for s in paragraphs[1:]:
            if s:
                self.add_package(s)

    def add_package(self, source=None):
        package = PackageParagraph(source or self.DEFAULT_PACKAGE_PARAGRAPH)
        self.packages.append(package)
        return package

    def get_dependencies(self):
        return chain(*(p.get('depends', []) for p in self.packages))

    def get_versioned_dependencies(self):
        return [d for d in self.get_dependencies() if d.is_versioned()]

    def get_packages(self):
        return [p['package'] for p in self.packages]

    def check_downgrade(self, current_version, new_version):
        """
        Raise ValueError if new_version is lower then current_version
        """
        curr_tuple = map(int, current_version.split("."))
        new_tuple = map(int, new_version.split("."))


        for i in xrange(0, len(curr_tuple)):
            if len(new_tuple) < (i+1):
                raise ValueError("Attempt to downgrade %s to %s (%s)" % (
                    current_version,
                    new_version,
                    self._pname,
                ))
            elif new_tuple[i] > curr_tuple[i]:
                return True
            elif (new_tuple[i] < curr_tuple[i]):
                raise ValueError("Attempt to downgrade %s to %s (%s)" % (
                    current_version,
                    new_version,
                    self._pname,
                ))
        return True

    def replace_dependencies(self, deps_from_repositories):
        new_versions = dict((p.name, p.version) for p in deps_from_repositories)
        for p in self.get_dependencies():
            if p.name in new_versions:
                self._pname = p.name
                new_version = new_versions[p.name]
                self.check_downgrade(p.version, new_version)
                p.version = new_version

    def replace_versioned_packages(self, version, old_version='0.0.0.0'):
        new_deps = []
        for p in self.get_packages():
            if p.version and p.version == old_version:
                p.version = version
                new_deps.append(p)
        self.replace_dependencies(new_deps)
    
    def dump(self, filename=None):
        out = '\n\n'.join(p.dump() for p in [self.source] + self.packages)
        if filename:
            fout = open(filename, 'w')
            fout.write(out)
            fout.close()
        return out


