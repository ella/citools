

from subprocess import check_call, Popen, PIPE
from helpers import PaverTestCase

class TestPaverVersioning(PaverTestCase):

    def test_version_computing(self):
        p = Popen(['paver', '-q', 'compute_version'], stdout=PIPE)
        stdout, stderr = p.communicate()
        self.assertEquals('0.0.1', stdout.strip())
