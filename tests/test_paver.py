

from subprocess import check_call, Popen, PIPE
from helpers import PaverTestCase

class TestPaverVersioning(PaverTestCase):

    def test_version_computes_default(self):
        p = Popen(['paver', '-q', 'compute_version'], stdout=PIPE)
        stdout, stderr = p.communicate()
        self.assertEquals('0.0.1', stdout.strip())

    def test_version_accepts_tag_with_default_pattern(self):
        check_call(['git', 'tag', '-a', 'exproject-2.3', '-m', '"Tagging"'])

        p = Popen(['paver', '-q', 'compute_version'], stdout=PIPE)
        stdout, stderr = p.communicate()
        self.assertEquals('2.3.0', stdout.strip())

    def test_paver_accepts_tag_pattern_as_argument(self):
        check_call(['git', 'tag', '-a', 'wtf-3.3', '-m', '"Tagging"'])

        p = Popen(['paver', '-q', 'compute_version', '--accepted-tag-pattern=wtf-[0-9]*'], stdout=PIPE)
        stdout, stderr = p.communicate()
        self.assertEquals('3.3.0', stdout.strip())

    def test_paver_accepts_tag_pattern_as_argument_in_original_alias(self):
        check_call(['git', 'tag', '-a', 'wtf-3.3', '-m', '"Tagging"'])

        p = Popen(['paver', '-q', 'compute_version_git', '--accepted-tag-pattern=wtf-[0-9]*'], stdout=PIPE)
        stdout, stderr = p.communicate()
        self.assertEquals('3.3.0', stdout.strip())


class TestDebianPackaging(PaverTestCase):

    def test_version_computing(self):
        p = Popen(['paver', '-q', 'compute_version'], stdout=PIPE)
        stdout, stderr = p.communicate()
        self.assertEquals('0.0.1', stdout.strip())
