from os import chdir
from os.path import join, abspath, dirname

from paver.easy import *
from paver.setuputils import setup

from setuptools import find_packages

VERSION = (0, 1)

__version__ = VERSION
__versionstr__ = '.'.join(map(str, VERSION))

setup(
    name = 'exproject',
    version = __versionstr__,
    description = 'example project',
    long_description = '\n'.join((
        'example project',
        '',
    )),
    author = 'centrum holdings',
    author_email='devs@centrumholdings.com',
    license = 'BSD',

    packages = find_packages(
        where = '.',
        exclude = ('docs', 'tests')
    ),

    include_package_data = True,

    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    setup_requires = [
        'setuptools_dummy',
    ],

    install_requires = [
        'setuptools>=0.6b1',
    ],
)

options(
    citools = Bunch(
        rootdir = abspath(dirname(__file__)),
        project_module = "exproject",
    ),
)

from citools.pavement import *
