from nose.plugins.skip import SkipTest
from pymongo.errors import ConnectionFailure

import os
from unittest import TestCase

from citools.mongo import get_mongo_and_database_connections


class MongoTestCase(TestCase):
    def setUp(self):
        try:
            self.database, self.connection = get_mongo_and_database_connections(
                hostname=os.environ.get("MONGODB_HOSTNAME", "localhost"),
                port=os.environ.get("MONGODB_PORT", None),
                database=os.environ.get("MONGODB_DATABASE", "test_citools"),
                username=None,
                password=None
            )
        except ConnectionFailure:
            raise SkipTest()


    def tearDown(self):
        self.connection.drop_database(self.database)