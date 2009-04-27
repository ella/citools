====================
CI tools
====================

Ultimate goal of Continuous Integration tools is to provide "integration button", magic key hit that will do everything needed for product to build & deploy. While there are some tools available, none of those fullfills our real-world needs.

Basic idea is simple: use setup.py in similar fashion as Makefiles or ant, but take advantage of setuptools plugin system to provide globally available commands, easily configurable for every project.

We are making some assumptions about project structure and needs. If you need to configure something more, let us know, or just `fork us at github <http://github.com/ella/citools/tree/master>`_ and send us Your pull request.

Licensed under `BSD <http://www.opensource.org/licenses/bsd-license.php>`_, this library is maintained by Ella team from Centrum Holdings. For feedback, ideas, bug reports and friends, let us know in `mailing list <http://groups.google.com/group/ella-project>`_.

.. toctree::
   :maxdepth: 2

----------------------------
On (continuous) versioning
----------------------------

----------------------------
(Django) web environment
----------------------------

----------------------------
Build process
----------------------------

----------------------------
Testing
----------------------------

----------------------------
Working with databases
----------------------------

Downloading backup::

    [backup]
    protocol = ftp
    username = blah
    password = xxx
    file = centrum/backup6/tmp/stdout.sql

    [database]
    name = stdout
    username = buildbot
    password = xxx

    citools -c /etc/$project/citools.ini db_restore

when run as setup.py db_restore, /etc/$project/citools.ini is the default


----------------------------
Distribution and Deployment
----------------------------


