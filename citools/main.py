"""
Main "entry point" module for package
"""
import os
import sys

from argparse import ArgumentParser

from citools.config import Configuration
from citools.backup import Backuper

__all__ = ('main',)

def restore_backup(config):
    backuper = Backuper(config)
    backuper.get_backup()
    backuper.restore_backup()
    backuper.clean_backup()
    return 0

def validate_arguments(config):
    print "Arguments are valid"
    return 0

def get_parser():
    """
    Construct command-line argument parser with all allowed options.
    Remember: if option should be propagated into config, then mapping must be
    specified in config.Configuration.NAMESPACE_CONFIG_MAP
    """
    
    parser = ArgumentParser(description='CI tools')
    parser.add_argument(
        '--config', type=unicode,
        help=u"Select action You want to take"
    )
    parser.add_argument(
        'command', type=unicode, choices=ACTIONS_MAP,
        help=u"Specify command You'd like to call"
    )
    return parser

def main(argv=None, config=None, do_exit=True):
    """
    Main entry point for console script
    """
    argv = argv or sys.argv[1:]
    parser = get_parser()
    namespace = parser.parse_args(argv)

    config = config or Configuration()
    config.command = namespace.command

    #TODO: Default config file is /etc/$project/citools.ini, but from command
    # line we have no idea what the $project is

    if namespace.config and os.path.exists(namespace.config) and os.path.isfile(namespace.config):
        config.read_config(namespace.config)

    config.merge_with_cmd(namespace)

    code = ACTIONS_MAP[config.command](config=config)

    if do_exit:
        sys.exit(code or 0)
    else:
        return code


ACTIONS_MAP = {
    "restore_backup" : restore_backup,
    "validate_arguments" : validate_arguments,
}