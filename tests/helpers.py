from nose.plugins.skip import SkipTest

import os
from unittest import TestCase



class MongoTestCase(TestCase):
    def setUp(self):
        try:
            from pymongo.errors import ConnectionFailure
            from citools.mongo import get_mongo_and_database_connections
        except ImportError, e:
            import traceback as t
            raise SkipTest("Error when importing dependencies (pymongo not installed?): %s" % t.format_exc())
        connection_arguments = {
            "hostname" : os.environ.get("MONGODB_HOSTNAME", "localhost"),
            "database" : os.environ.get("MONGODB_DATABASE_NAME", "test_citools")
        }

        if os.environ.get("MONGODB_PORT", None):
            connection_arguments['port'] = os.environ.get("MONGODB_PORT", None)

        if os.environ.get("MONGODB_USERNAME", None):
            connection_arguments['username'] = os.environ.get("MONGODB_USERNAME", None)

        if os.environ.get("MONGODB_PASSWORD", None):
            connection_arguments['password'] = os.environ.get("MONGODB_PASSWORD", None)

        try:
            self.database, self.connection = get_mongo_and_database_connections(
                **connection_arguments
            )
        except ConnectionFailure:
            raise SkipTest("Cannot connect to mongo database, check your settings")


    def tearDown(self):
        self.connection.drop_database(self.database)
