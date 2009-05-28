# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

__versionstr__ = '0.0.1.0'
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
	"This package provides a set of setuptools plugins (setup.py commands)",
	"to provide required functionality and make CI a breeze.",
	"Main aim of this project are Django-based applications, but it's usable",
	"for generic python projects as well.",
    )),
    author = 'centrum holdings s.r.o',
    author_email='devel@centrumholdings.com',
    license = 'BSD',
    url='http://github.com/ella/citools/tree/master',

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
        ],
        'distutils.commands' : [
            'compute_version_git = citools.version:GitSetVersion',
            'compute_version_meta_git = citools.version:GitSetMetaVersion',
        ],
    },
    install_requires = [
        'setuptools>=0.6b1',
        'argparse>=0.9.0',
    ],
)

