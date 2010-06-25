import sys
from urllib import quote_plus, urlencode
from urllib2 import URLError
from urllib2 import urlopen
from urlparse import urljoin

from argparse import ArgumentParser


def force_build(argv=None, config=None, do_exit=True):

    from anyjson import serialize

    parser = ArgumentParser(description='CI tools CthulhuBot Build Forcer')
    parser.add_argument(
        '--branch', type=unicode,
        help=u"What branch would You like to build"
    )
    parser.add_argument(
        '--changeset', type=unicode,
        help=u"Which hangeset would You like build"
    )
    parser.add_argument(
        'uri', type=unicode,
        help=u"Cut & paste URI of an assignment to be forced from Your CthulhuBot web interface"
    )

    namespace = parser.parse_args(argv)

    uri = urljoin(namespace.uri, "force")+"/"

    args = {}

    for i in ['branch', 'changeset']:
        if hasattr(namespace, i):
            args[i] = getattr(namespace, i)

    f = None
    try:
        f = urlopen(uri, data=urlencode([("data", quote_plus(serialize(args)))]))
        print f.read()
    except URLError, e:
        print e.fp.read()
        raise
    finally:
        if f:
            f.close()

    code = 0

    if do_exit:
        sys.exit(code or 0)
    else:
        return code

