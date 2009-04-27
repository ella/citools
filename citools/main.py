"""
Main "entry point" module for package
"""
import sys

from citools.config import get_config


__all__ = ('main',)

def main(argv=sys.argv):
    """
    Main entry point for console script
    """
    config = get_config(argv=argv)
    