"""
CI tools is a collection of small configurations aimed to ease setting up
complete CI system, targettet on django apps.
"""
VERSION = (0, 0, 1, 0)

__version__ = VERSION
__versionstr__ = '.'.join(map(str, VERSION))

from citools.main import main
