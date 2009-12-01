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
            raise SkipTest("Error when importing dependencies (pymongo not installed?): %s" % t.format_exception())
        try:
            self.database, self.connection = get_mongo_and_database_connections(
                hostname=os.environ.get("MONGODB_HOSTNAME", "localhost"),
                port=os.environ.get("MONGODB_PORT", None),
                database=os.environ.get("MONGODB_DATABASE", "test_citools"),
                username=None,
                password=None
            )
        except ConnectionFailure:
            raise SkipTest("Cannot connect to mongo database, check your settings")


    def tearDown(self):
        self.connection.drop_database(self.database)