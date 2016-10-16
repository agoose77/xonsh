import os
import sys
import shutil
import subprocess

import pytest

import xonsh
from xonsh.platform import ON_WINDOWS

from tools import skip_if_on_windows


XONSH_PREFIX = xonsh.__file__
if 'site-packages' in XONSH_PREFIX:
    # must be installed version of xonsh
    num_up = 5
else:
    # must be in source dir
    num_up = 2
for i in range(num_up):
    XONSH_PREFIX = os.path.dirname(XONSH_PREFIX)
PATH = os.path.join(os.path.dirname(__file__), 'bin') + os.pathsep + \
       os.path.join(XONSH_PREFIX, 'bin') + os.pathsep + \
       os.path.join(XONSH_PREFIX, 'Scripts') + os.pathsep + \
       os.path.join(XONSH_PREFIX, 'scripts') + os.pathsep + \
       os.path.dirname(sys.executable) + os.pathsep + \
       os.environ['PATH']


def run_xonsh(cmd):
    env = dict(os.environ)
    env['PATH'] = PATH
    env['XONSH_DEBUG'] = '1'
    env['XONSH_SHOW_TRACEBACK'] = '1'
    env['RAISE_SUBPROC_ERROR'] = '1'
    env['PROMPT'] = ''
    xonsh = 'xonsh.bat' if ON_WINDOWS else 'xon.sh'
    xonsh = shutil.which(xonsh, path=PATH)
    proc = subprocess.Popen([xonsh, '--no-rc'],
                            env=env,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            universal_newlines=True,
                            )
    try:
        out, err = proc.communicate(input=cmd, timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise
    return out, err, proc.returncode

#
# The following list contains a (stdin, stdout, returncode) tuples
#

ALL_PLATFORMS = [
# test calling a function alias
("""
def _f():
    print('hello')

aliases['f'] = _f
f
""", "hello\n", 0),
# test redirecting a function alias
("""
def _f():
    print('Wow Mom!')

aliases['f'] = _f
f > tttt

with open('tttt') as tttt:
    s = tttt.read().strip()
print('REDIRECTED OUTPUT: ' + s)
""", "REDIRECTED OUTPUT: Wow Mom!\n", 0),
# test system exit in function alias
("""
import sys
def _f():
    sys.exit(42)

aliases['f'] = _f
print(![f].returncode)
""", "42\n", 0),
# test uncaptured streaming alias
("""
def _test_stream(args, stdin, stdout, stderr):
    print('hallo on err', file=stderr)
    print('hallo on out', file=stdout)
    return 1

aliases['test-stream'] = _test_stream
x = ![test-stream]
print(x.returncode)
""", "hallo on out\nhallo on err\n1\n", 0),
# test captured streaming alias
("""
def _test_stream(args, stdin, stdout, stderr):
    print('hallo on err', file=stderr)
    print('hallo on out', file=stdout)
    return 1

aliases['test-stream'] = _test_stream
x = !(test-stream)
print(x.returncode)
""", "hallo on err\n1\n", 0),
]


@pytest.mark.parametrize('case', ALL_PLATFORMS)
def test_script(case):
    script, exp_out, exp_rtn = case
    out, err, rtn = run_xonsh(script)
    assert exp_out == out
    assert exp_rtn == rtn


@skip_if_on_windows
@pytest.mark.parametrize('cmd, fmt, exp', [
    ('pwd', None, os.getcwd() + '\n'),
    ('echo WORKING', None, 'WORKING\n'),
    ('ls -f', lambda out: out.splitlines().sort(), os.listdir().sort()),
    ])
def test_single_command(cmd, fmt, exp):
    """The ``fmt`` parameter is a function
    that formats the output of cmd, can be None.
    """
    out, err, rtn = run_xonsh(cmd)
    if callable(fmt):
        out = fmt(out)
    assert out == exp
    assert rtn == 0


@skip_if_on_windows
@pytest.mark.parametrize('cmd, exp', [
    ('pwd', os.getcwd() + '\n'),
    ])
def test_redirect_out_to_file(cmd, exp, tmpdir):
    outfile = tmpdir.mkdir('xonsh_test_dir').join('xonsh_test_file')
    command = '{} > {}'.format(cmd, outfile)
    out, _, _ = run_xonsh(command)
    content = outfile.read()
    assert content == exp
