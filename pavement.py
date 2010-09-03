#!/usr/bin/env python
import os
import sys
from os.path import abspath, dirname

from paver.easy import *
from paver.setuputils import setup

from setuptools import find_packages

VERSION = (0, 2, 0)
__version__ = VERSION
__versionstr__ = '.'.join(map(str, VERSION))

setup(
    name = 'citools',
    version = __versionstr__,
    description = 'Coolection of plugins to help with building CI system',
    long_description = '\n'.join((
        'CI Tools',
        '',
        'Ultimate goal of CI system is to provide single "integration button"',
        'to automagically do everything needed for creating a release',
        "(and ensure it's properly build version).",
        '',
        "This package provides a set of setuptools plugins (setup.py commands)",
        "to provide required functionality and make CI a breeze.",
        "Main aim of this project are Django-based applications, but it's usable",
        "for generic python projects as well.",
    )),
    author = 'centrum holdings s.r.o',
    author_email='devel@centrumholdings.com',
    license = 'BSD',
    url='http://github.com/ella/citools/tree/master',

    test_suite = 'nose.collector',

    packages = find_packages(
        where = '.',
        exclude = ('docs', 'tests')
    ),

    include_package_data = True,

    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    entry_points = {
        'console_scripts': [
            'citools = citools.main:main',
            'cthulhubot_force_build = citools.cthulhubot:force_build',
        ],
    },
    install_requires = [
        'setuptools>=0.6b1',
        'argparse>=0.9.0',
        'pyparsing',
    ],
)


options(
    citools = Bunch(
        rootdir = abspath(dirname(__file__))
    ),
)

try:
    from citools.pavement import *
except ImportError:
    pass

@task
def install_dependencies():
    sh('pip install --upgrade -r requirements.txt')

@task
@consume_args
def unit(args):
    import nose
    nose.run_exit(
        argv = ["nosetests"] + args
    )

@task
def bootstrap():
    options.virtualenv = {'packages_to_install' : ['pip']}
    call_task('paver.virtual.bootstrap')
    sh("python bootstrap.py")
    path('bootstrap.py').remove()


    print '*'*80
    if sys.platform in ('win32', 'winnt'):
        print "* Before running other commands, You now *must* run %s" % os.path.join("bin", "activate.bat")
    else:
        print "* Before running other commands, You now *must* run source %s" % os.path.join("bin", "activate")
    print '*'*80

@task
@needs('install_dependencies')
def prepare():
    """ Prepare complete environment """
    sh("python setup.py develop")

