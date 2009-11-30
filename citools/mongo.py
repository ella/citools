from pymongo.son_manipulator import AutoReference
from pymongo.son_manipulator import NamespaceInjector
from pymongo.connection import Connection

import logging

log = logging.getLogger("citools.mongo")

def get_mongo_and_database_connections(hostname=None, port=None, database=None, username=None, password=None):
    connection = Connection(hostname, port)

    database = connection[database]

    database.add_son_manipulator(NamespaceInjector())
    database.add_son_manipulator(AutoReference(database))

    if username or password:
        auth = database.authenticate(username, password)
        if auth is not True:
            log.msg("FATAL: Not connected to Mongo Database, authentication failed")
            raise AssertionError("Not authenticated to use selected database")

    return (database, connection)


def get_database_connection(hostname=None, port=None, database=None, username=None, password=None):
    return get_mongo_and_database_connections(hostname=hostname, port=port, database=database, username=username, password=password)[0]
