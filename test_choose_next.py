# -*- coding: utf-8 -*-

# Copyright (C) 2010-2017 Johannes Weißl
# License GPLv3+:
# GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
# This is free software: you are free to change and redistribute it.
# There is NO WARRANTY, to the extent permitted by law.

"""Test module for choose_next.py."""

from __future__ import print_function
import sys
import os
import re
import unittest
import tempfile
import shutil
from io import StringIO
import subprocess
import stat

import choose_next

def mkdir_p(path):
    """Like os.makedirs(), but ignores existing directories."""
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise

def fake_sys_exit(arg=0):
    """Raise exception instead of exiting, for testing."""
    raise Exception('sys.exit({!r})'.format(arg))

def choose_next_main(*args):
    """Call choose_next.py main function, return captured standard output."""
    original_stdout = sys.stdout
    stdout_buffer = StringIO()
    sys.stdout = stdout_buffer
    try:
        choose_next.main_throws(list(args))
        return stdout_buffer.getvalue()
    finally:
        sys.stdout = original_stdout

def choose_next_external(*args):
    """Call choose_next.py as external process."""
    here = os.path.abspath(os.path.dirname(__file__))
    prog = os.path.join(here, 'choose_next.py')
    shell = False
    if os.name == 'nt':
        shell = True
    return subprocess.check_output([prog] + list(args), stderr=subprocess.STDOUT, shell=shell,
                                   universal_newlines=True)

def put_file(dirname, filename):
    """Put file into directory and return absolute path."""
    path = os.path.join(dirname, filename)
    mkdir_p(os.path.dirname(path))
    with open(path, 'w') as stream:
        stream.write(filename)
    return path

def put_files(dirname, *filenames):
    """Put files into directory and return absolute paths."""
    return [put_file(dirname, filename) for filename in filenames]

class ChooseNextTestCase(unittest.TestCase):
    # pylint: disable=too-many-public-methods
    # pylint: disable=deprecated-method
    """Main choose_next.py test class."""

    @classmethod
    def setUpClass(cls):
        """Add renamed member functions for Python 2.7."""
        if sys.version_info < (3, 2):
            cls.assertRegex = cls.assertRegexpMatches
            cls.assertRaisesRegex = cls.assertRaisesRegexp

    def setUp(self):
        """Create temporary directory."""
        self.tmpdir = os.path.realpath(tempfile.mkdtemp())
        self.logdir = os.path.realpath(tempfile.mkdtemp())
        os.environ['CHOOSE_NEXT_LOGDIR'] = self.logdir

    def tearDown(self):
        """Remove temporary directory."""
        del os.environ['CHOOSE_NEXT_LOGDIR']
        shutil.rmtree(self.logdir)
        shutil.rmtree(self.tmpdir)

    def put_file(self, filename):
        """Put file into the temporary directory and return absolute path."""
        return put_file(self.tmpdir, filename)

    def put_files(self, *filenames):
        """Put files into the temporary directory and return absolute paths."""
        return [self.put_file(filename) for filename in filenames]

    def put_dir(self, dirname):
        """Put directory into the temporary directory and return absolute path."""
        path = os.path.join(self.tmpdir, dirname)
        mkdir_p(path)
        return path

    def put_dirs(self, *dirnames):
        """Put directories into the temporary directory and return absolute paths."""
        return [self.put_dir(dirname) for dirname in dirnames]

    def test_mkdir_p(self):
        """Test internal function for coverage."""
        file1, file2 = self.put_files('a/b', 'a/c')
        dir1, dir2 = self.put_dirs('c', 'c/d')
        self.assertTrue(os.path.isfile(file1))
        self.assertTrue(os.path.isfile(file2))
        self.assertTrue(os.path.isdir(dir1))
        self.assertTrue(os.path.isdir(dir2))
        with self.assertRaises(OSError):
            self.put_dirs('a/b')

    def test_basic(self):
        """Test basic functionality."""
        file_a, file_b, file_c = self.put_files('a', 'b', 'c')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_c + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir))

    def test_empty(self):
        """Raise error if called on empty directory."""
        with self.assertRaisesRegex(choose_next.Error, 'no files available'):
            choose_next_main(self.tmpdir)

    def test_main(self):
        """Test main function for coverage."""
        original_sys_exit = sys.exit
        sys.exit = fake_sys_exit
        with self.assertRaisesRegex(Exception, r'^sys.exit\(0\)$'):
            choose_next.main(['--help'])
        sys.exit = original_sys_exit

    def test_main_error(self):
        """Test main function error for coverage."""
        original_sys_exit = sys.exit
        sys.exit = fake_sys_exit
        with self.assertRaisesRegex(Exception, r'^sys.exit\(1\)$'):
            choose_next.main([os.path.join(self.tmpdir, 'nonexist')])
        sys.exit = original_sys_exit

    def test_nodirectory_specified(self):
        """Raise error if directory is not specified."""
        original_sys_exit = sys.exit
        sys.exit = fake_sys_exit
        with self.assertRaisesRegex(Exception, r'^sys.exit\(2\)$'):
            choose_next_main()
        sys.exit = original_sys_exit

    def test_nonexisting(self):
        """Raise error if directory does not exist."""
        with self.assertRaisesRegex(choose_next.Error, 'error listing'):
            choose_next_main(os.path.join(self.tmpdir, 'nonexist'))

    def test_nodirectory(self):
        """Raise error if path is no directory."""
        self.put_files('nodirectory')
        with self.assertRaisesRegex(choose_next.Error, 'error listing'):
            choose_next_main(os.path.join(self.tmpdir, 'nodirectory'))

    def test_help(self):
        """Check that '-h' and '--help' options work."""
        help_output1 = choose_next_external('-h')
        help_output2 = choose_next_external('--help')
        self.assertRegex(help_output1, '^usage: choose_next')
        self.assertEqual(help_output1, help_output2)

    def test_version(self):
        """Check that the '--version' option works."""
        here = os.path.abspath(os.path.dirname(__file__))
        setup_prog = os.path.join(here, 'setup.py')
        version = subprocess.check_output(['python', setup_prog, '--version'],
                                          universal_newlines=True)
        version_output = choose_next_external('--version')
        self.assertRegex(version_output, '^choose_next.py ' + re.escape(version))

    def test_dump(self):
        """Check that the '--dump' option works."""
        file_a, file_b = self.put_files('a', 'b')
        self.assertEqual('', choose_next_main(self.tmpdir, '--dump'))
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir))
        self.assertEqual('a\n', choose_next_main(self.tmpdir, '--dump'))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir))
        self.assertEqual('a\nb\n', choose_next_main(self.tmpdir, '--dump'))

    def test_quiet(self):
        """Check that '-q' and '--quiet' options work."""
        self.put_files('a', 'b')
        self.assertEqual('', choose_next_main(self.tmpdir, '-q'))
        self.assertEqual('', choose_next_main(self.tmpdir, '--quiet'))
        self.assertEqual('a\nb\n', choose_next_main(self.tmpdir, '--dump'))

    def test_verbose(self):
        """Check that '-v' and '--verbose' options work."""
        file_a, file_b = self.put_files('a', 'b')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir, '--verbose'))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir, '-v', '-v', '-v', '-v'))

    def test_command(self):
        """Check that '-c' and '--command' options work."""
        file_a1, file_a2 = self.put_files('a1', 'a2')
        pysed = (
            'python -c "'
            'from sys import argv as a;'
            's = open(a[1]).read();'
            'open(a[1], \'w\').write(s.replace(\'a\', \'b\'))'
            '"'
        )
        self.assertEqual(file_a1 + '\n', choose_next_main(self.tmpdir, '-c', pysed))
        self.assertEqual(file_a2 + '\n', choose_next_main(self.tmpdir, '--command', pysed))
        self.assertEqual('b1', open(file_a1).read())
        self.assertEqual('b2', open(file_a2).read())
        with self.assertRaisesRegex(choose_next.Error, 'command failed'):
            choose_next_main(self.tmpdir, '-c' 'python -c "exit(1)"')

    def test_no_write(self):
        """Check that '-w' and '--no-write' options work."""
        file_a, file_b = self.put_files('a', 'b')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir, '-w'))
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir, '--no-write'))
        self.assertEqual('', choose_next_main(self.tmpdir, '--dump'))
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir))

    def test_no_read(self):
        """Check that '-i' and '--no-read' options work."""
        file_a, file_b = self.put_files('a', 'b')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir, '-i'))
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir, '--no-read'))
        self.assertEqual('a\n', choose_next_main(self.tmpdir, '--dump'))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir))

    def test_last(self):
        """Check that '-l' and '--last' options work."""
        file_a, file_b, file_c = self.put_files('a', 'b', 'c')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir, '-l'))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir, '--last'))
        self.assertEqual(file_c + '\n', choose_next_main(self.tmpdir))

    def test_clear(self):
        """Check that the '--clear' option works."""
        file_a, file_b, _unused = self.put_files('a', 'b', 'c')
        choose_next_main(self.tmpdir, '--clear')
        self.assertEqual('', choose_next_main(self.tmpdir, '--dump'))
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir))
        self.assertEqual('a\nb\n', choose_next_main(self.tmpdir, '--dump'))
        choose_next_main(self.tmpdir, '--clear')
        self.assertEqual('', choose_next_main(self.tmpdir, '--dump'))
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir))

    def test_clear_error(self):
        """Check that the '--clear' option can handle errors."""
        file_a, _unused, _unused = self.put_files('a', 'b', 'c')
        logdir = tempfile.mkdtemp()
        logfile = os.path.join(logdir, 'logfile')
        choose_next_main(self.tmpdir, '--logfile', logfile, '--clear')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir, '--logfile', logfile))
        os.chmod(logfile, stat.S_IREAD)
        os.chmod(logdir, stat.S_IREAD)
        with self.assertRaisesRegex(choose_next.Error, 'error removing logfile'):
            choose_next_main(self.tmpdir, '--logfile', logfile, '--clear')
        os.chmod(logdir, stat.S_IWRITE | stat.S_IEXEC | stat.S_IREAD)
        os.chmod(logfile, stat.S_IWRITE | stat.S_IREAD)
        shutil.rmtree(logdir)

    def test_clear_last(self):
        """Check that the '--clear-last' option works."""
        file_a, file_b, _unused = self.put_files('a', 'b', 'c')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir))
        choose_next_main(self.tmpdir, '--clear-last')
        self.assertEqual('a\n', choose_next_main(self.tmpdir, '--dump'))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir))

    def test_clear_first(self):
        """Check that the '--clear-first' option works."""
        file_a, file_b, file_c = self.put_files('a', 'b', 'c')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir))
        choose_next_main(self.tmpdir, '--clear-first')
        self.assertEqual('b\n', choose_next_main(self.tmpdir, '--dump'))
        self.assertEqual(file_c + '\n', choose_next_main(self.tmpdir))

    def test_recursive_default(self):
        """Check that recursive directory reading works by default."""
        file_a, file_b, file_c, file_d = self.put_files('x/y/a', 'x/y/b', 'y/c', 'z')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_c + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_d + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir))

    def test_no_recursive(self):
        """Check that '-N' and '--no-recursive' options work."""
        _unused, _unused, _unused, file_d = self.put_files('x/y/a', 'x/y/b', 'y/c', 'z')
        self.assertEqual(file_d + '\n', choose_next_main(self.tmpdir, '-N'))
        self.assertEqual(file_d + '\n', choose_next_main(self.tmpdir, '--no-recursive'))

    def test_recursive(self):
        """Check that '-R' and '--recursive' options work."""
        file_a, file_b, file_c, file_d = self.put_files('x/y/a', 'x/y/b', 'y/c', 'z')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir, '-N', '--recursive'))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir, '-N', '-R'))
        self.assertEqual(file_c + '\n', choose_next_main(self.tmpdir, '--recursive'))
        self.assertEqual(file_d + '\n', choose_next_main(self.tmpdir, '-R'))
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir, '-R'))

    def test_prepend(self):
        """Check that '-p' and '--prepend' options work."""
        file_a, file_b, file_c = self.put_files('a', 'b', 'c')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir, '-p'))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir, '-p'))
        self.assertEqual('b\na\n', choose_next_main(self.tmpdir, '--dump'))
        self.assertEqual(file_c + '\n', choose_next_main(self.tmpdir, '--prepend'))
        self.assertEqual('c\nb\na\n', choose_next_main(self.tmpdir, '--dump'))

    def test_number(self):
        """Check that '-n' and '--number' options work."""
        file_a, file_b = self.put_files('a', 'b')
        self.assertEqual(file_a + '\n' + file_b + '\n', choose_next_main(self.tmpdir, '-n', '2'))
        # TODO: More tests

    def test_include_directories(self):
        """Check that '-d' and '--include-directories' options work."""
        file_b, file_c = self.put_dirs('b', 'c')
        file_a, file_bb = self.put_files('a', 'b/b')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir, '-d'))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir, '--include-directories'))
        self.assertEqual(file_bb + '\n', choose_next_main(self.tmpdir, '-d'))
        self.assertEqual(file_c + '\n', choose_next_main(self.tmpdir, '-d'))

    def test_exclude(self):
        """Check that the '--exclude' option works."""
        file_a, file_b = self.put_files('a.mp3', 'b.wav')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir, '--exclude', '*.ogg'))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir, '--exclude', '*.mp3'))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir, '--exclude', '*.mp3'))

    def test_include(self):
        """Check that the '--include' option works."""
        file_a, file_b = self.put_files('a.mp3', 'b.mp3')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir, '--include', '*.mp3'))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir, '--include', '*.wav'))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir,
                                                         '--exclude', '*.mp3',
                                                         '--include', '*/b.*'))

    def test_files(self):
        """Check that filename arguments work."""
        file_a, file_b, file_c = self.put_files('a', 'b', 'c')
        file_nonexist = os.path.join(self.tmpdir, 'x')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir, file_a))
        self.assertEqual(file_c + '\n', choose_next_main(self.tmpdir, file_c))
        self.assertEqual('a\nc\n', choose_next_main(self.tmpdir, '--dump'))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_nonexist + '\n', choose_next_main(self.tmpdir, file_nonexist))
        with self.assertRaisesRegex(choose_next.Error, 'leads outside given directory'):
            choose_next_main(self.tmpdir, os.path.join(self.logdir, 'outside'))

    def test_repeat(self):
        """Check that repeating works even if no remaining files follow."""
        file_a, file_b, file_c = self.put_files('a', 'b', 'c')
        self.assertEqual(file_c + '\n', choose_next_main(self.tmpdir, file_c))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir, file_b))
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir))

    def test_random(self):
        """Check that '-r' and '--random' options work."""
        names = ['{:02d}'.format(i) for i in range(0, 50)]
        files = self.put_files(*names)
        def random_files(*args):
            """Choose files in random fashion."""
            return [choose_next_main(self.tmpdir, '-r', *args).rstrip('\n') for _name in files]
        self.assertEqual(files, sorted(random_files()))
        self.assertNotEqual(random_files(), random_files())  # very unlikely to fail

    def test_numeric_sort(self):
        """Check that files are sorted numerically."""
        # FIXME, should work, too:
        # a, b, c = self.put_files('s 2/3 e', 's 2/20 e', 's 10/5 e')
        file_a, file_b, file_c = self.put_files('2/3 e', '2/20 e', '10/5 e')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_c + '\n', choose_next_main(self.tmpdir))

    def test_logfile(self):
        """Check that '-L' and '--logfile' options work."""
        logdir = tempfile.mkdtemp()
        logfile = os.path.join(logdir, 'logfile')
        file_a, file_b, _unused = self.put_files('a', 'b', 'c')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir, '-L', logfile))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir, '--logfile', logfile))
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir))
        with self.assertRaisesRegex(choose_next.Error, 'error reading logfile'):
            choose_next_main(self.tmpdir, '--logfile', self.tmpdir)
        choose_next.logfile_append(logfile, os.path.join(self.logdir, 'outside'))
        with self.assertRaisesRegex(choose_next.Error, 'leads outside given directory'):
            choose_next_main(self.tmpdir, '--logfile', logfile)
        shutil.rmtree(logdir)

    def test_nonexist_logdir(self):
        """Check non-existing logdir for coverage."""
        shutil.rmtree(self.logdir)
        file_a, file_b = self.put_files('a', 'b')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir))

    def test_nonexist_logdir_error(self):
        """Check handling of error when creating logdir for coverage."""
        shutil.rmtree(self.logdir)
        with open(self.logdir, 'w') as stream:
            stream.write('logdir\n')
        self.put_files('a', 'b')
        with self.assertRaisesRegex(choose_next.Error, 'error creating logdir'):
            choose_next_main(self.tmpdir)
        os.unlink(self.logdir)
        os.makedirs(self.logdir)

    def test_hidden(self):
        """Check that hidden files are not chosen."""
        file_a, _unused, file_c = self.put_files('a', '.b', 'c')
        _unused, file_e = self.put_dirs('.d', 'e')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir, '-d'))
        self.assertEqual(file_c + '\n', choose_next_main(self.tmpdir, '-d'))
        self.assertEqual(file_e + '\n', choose_next_main(self.tmpdir, '-d'))
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir, '-d'))

    def test_hidden_recursive(self):
        """Check that hidden files are not chosen in recursive mode."""
        file_a, _unused, _unused = self.put_files('x/y/a', 'x/.y/b', 'x/y/.c')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir, '-r'))
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir, '-r'))

    def test_multibyte_error(self):
        """Check that multibyte error message works."""
        with self.assertRaisesRegex(choose_next.Error, 'error listing'):
            choose_next_main(os.path.join(self.tmpdir, '\xc3\xa4'))
        with self.assertRaisesRegex(choose_next.Error, 'error listing'):
            choose_next_main(os.path.join(self.tmpdir, '\xe4'))

    def test_logfile_name_clash(self):
        """Check that mapping of directory to logfile name has no clash."""
        tmpdir1 = os.path.join(self.tmpdir, 'foo_bar')
        tmpdir2 = os.path.join(self.tmpdir, 'foo', 'bar')
        file_a1, _unused = put_files(tmpdir1, 'a', 'b')
        file_a2, _unused = put_files(tmpdir2, 'a', 'b')
        self.assertEqual(file_a1 + '\n', choose_next_main(tmpdir1))
        self.assertEqual(file_a2 + '\n', choose_next_main(tmpdir2))

    def test_logfile_name_migration(self):
        """Check that migration of logfile name works."""
        file_a, file_b, file_c = self.put_files('a', 'b', 'c')
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_b + '\n', choose_next_main(self.tmpdir))
        old_logfile = os.path.join(self.logdir, self.tmpdir.replace(os.path.sep, '_'))
        new_logfile = os.path.join(self.logdir, choose_next.quote_plus(self.tmpdir))
        os.rename(new_logfile, old_logfile)
        self.assertEqual(file_c + '\n', choose_next_main(self.tmpdir))
        self.assertEqual(file_a + '\n', choose_next_main(self.tmpdir))

    # TODO: newlines in files
    # TODO: prune stale entries from logfile

if __name__ == '__main__':
    unittest.main(buffer=True, catchbreak=True)
