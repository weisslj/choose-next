#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2010-2017 Johannes Weißl
# License GPLv3+:
# GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
# This is free software: you are free to change and redistribute it.
# There is NO WARRANTY, to the extent permitted by law.

"""Choose a file from a directory. Very handy to re-watch tv series!"""

from __future__ import print_function
import sys
import os
import re
import locale
import random
import subprocess
import fnmatch
import errno
import argparse
import shlex
import pipes
import logging
from itertools import islice, cycle, count

if sys.version_info < (3, 0):
    from itertools import ifilter as filter  # pylint: disable=no-name-in-module,redefined-builtin
if sys.version_info < (3, 2):
    os.fsencode = lambda filename: filename
if sys.version_info < (3, 3):
    shlex.quote = pipes.quote
try:
    from urllib.parse import quote_plus  # pylint: disable=no-name-in-module,import-error
except ImportError:  # Python 2 compatibility
    from urllib import quote_plus  # pylint: disable=no-name-in-module

MAKEDIRS = os.makedirs
if sys.version_info < (3, 4):
    def makedirs_compat(name, exist_ok=False, **kwargs):
        """Compatibility function with Python 3.4 os.makedirs()."""
        try:
            os.makedirs(name, **kwargs)
        except OSError:
            # This is broken in Python 3.2 and 3.3, cf. https://bugs.python.org/issue13498
            if not exist_ok or not os.path.isdir(name):
                raise
    MAKEDIRS = makedirs_compat

class Error(Exception):
    """Abort program, used in test suite."""
    pass

def read_dir_error(exc):
    """Raise Error exception on read_dir error."""
    raise Error('error listing {}: {}'.format(exc.filename, exc.strerror))

def remove_hidden(names):
    """Remove entries starting with a dot (.) from list of basenames."""
    names[:] = [name for name in names if not name.startswith('.')]

def read_dir(path, recursive=False, exclude=None, include=None, include_directories=False):
    """Return a list of paths in directory at path (recursively)."""
    paths = []
    for root, dirs, files in os.walk(path, onerror=read_dir_error):
        remove_hidden(dirs)
        remove_hidden(files)
        names = files
        if include_directories:
            names += dirs
        for name in names:
            abspath = os.path.join(root, name)
            if not exclude or \
                    ((not fnmatch.fnmatch(abspath, exclude)) or \
                    (include and fnmatch.fnmatch(abspath, include))):
                paths.append(os.path.relpath(abspath, path))
        if not recursive:
            break
    return paths

def make_relpath(path, start=os.curdir):
    """Return relative path to start directory, raise error if it leads outside."""
    try:
        relpath = os.path.relpath(path, start)
        if relpath.startswith(os.pardir + os.sep):
            raise Error('error, path {} leads outside given directory'.format(path))
        return relpath
    except ValueError as exc:  # only on Windows, e.g. if drive letters differ
        raise Error('{}: {}'.format(path, exc))

def logfile_entry_to_path(entry, dirpath):
    """Convert logfile entry to relative path."""
    path = entry if os.path.isabs(entry) else os.path.join(dirpath, entry)
    return make_relpath(path, dirpath)

def read_logfile(path, dirpath):
    """Return list of logfile entries."""
    try:
        with open(path, 'r') as stream:
            content = stream.read()
            entries = content.split('\0')[:-1] if '\0' in content else content.splitlines()
            return [logfile_entry_to_path(entry, dirpath) for entry in entries]
    except IOError as exc:
        if exc.errno == errno.ENOENT:
            return []
        else:
            raise Error('error reading logfile {}: {}'.format(path, exc.strerror))

def write_logfile(path, entries):
    """Write logfile entries to path."""
    with open(path, 'wb') as stream:
        stream.write(b''.join(os.fsencode(entry) + b'\0' for entry in entries))

NUMKEY_REGEX = re.compile(r'(\s*[+-]?[0-9]+\.?[0-9]*\s*)(.*)')
def numkey(string):
    """Return a sort key that works for filenames like '23 - foo'."""
    match = NUMKEY_REGEX.match(string)
    if match:
        return float(match.group(1)), locale.strxfrm(match.group(2))
    return (0.0, locale.strxfrm(string))

def path_split_all(path):
    """Return a list of path elements, e.g. 'a/b/..//c' -> ['a', 'c']."""
    return os.path.normpath(path).split(os.sep)

def numkey_path(path):
    """Return a sort key that works for paths like '2/23 - foo'."""
    return tuple(numkey(s) for s in path_split_all(path))

def play_next_file(next_file, logfile_content_list, args):
    """Part of main functionality."""
    logging.info('selected file: %s', next_file)
    next_file_abs = os.path.join(args.dir, next_file)
    #
    retval = 0
    if args.command:
        next_file_quoted = shlex.quote(next_file_abs)
        try:
            command = args.command % next_file_quoted
        except TypeError:
            command = args.command + ' ' + next_file_quoted
        logging.info('executing command: %s', command)
        retval = subprocess.call(command, shell=True)
    #
    if args.verbosity > 0:
        msg = next_file_abs
        if sys.version_info < (3, 0):
            msg = msg.decode(errors='replace')
        print(msg)
    #
    if retval == 0 and not args.no_write:
        if next_file not in logfile_content_list:
            if args.prepend:
                new_logfile_content_list = [next_file] + logfile_content_list
            else:
                new_logfile_content_list = logfile_content_list + [next_file]
            write_logfile(args.logfile, new_logfile_content_list)
    #
    return retval

def choose_next_file(args, next_file=None):
    """Part of main functionality."""
    logfile_content_list = read_logfile(args.logfile, args.dir)
    #
    played_list = logfile_content_list if not args.no_read else []
    played = set(played_list)
    #
    available = set(read_dir(args.dir, recursive=args.recursive, exclude=args.exclude,
                             include=args.include,
                             include_directories=args.include_directories))
    available_list = sorted(available, key=numkey_path)
    #
    remaining = available - played
    if not remaining:
        logging.info('truncating logfile (was full)')
        logfile_content_list = []
        remaining = available
    remaining_list = sorted(remaining, key=numkey_path)
    #
    logging.info('directory to choose from: %s', args.dir)
    logging.info('logfile: %s', args.logfile)
    logging.info('files available: %s', len(available))
    for path in available_list:
        logging.debug(path)
    logging.info('files in logfile: %s', len(played))
    for path in played_list:
        logging.debug(path)
    logging.info('files remaining for selection: %s', len(remaining))
    for path in remaining_list:
        logging.debug(path)
    #
    if not remaining:
        raise Error('error, no files available in {}'.format(args.dir))
    #
    if next_file:
        pass
    elif args.last and played_list:
        next_file = played_list[-1]
    elif args.random:
        next_file = random.choice(remaining_list)
    else:
        index = 0
        if played_list:
            last_file = played_list[-1]
            logging.info('last selected file: %s', last_file)
            if last_file in available:
                index = available_list.index(last_file) + 1
        next_file = next(filter(lambda path: path in remaining,
                                islice(cycle(available_list), index, None)))
    return next_file, logfile_content_list

def choose_next(args):
    """Main functionality."""
    for i in range(args.number) if args.number >= 0 else count():
        next_file = args.files[i] if i < len(args.files) else None
        next_file, logfile_content_list = choose_next_file(args, next_file)
        retval = play_next_file(next_file, logfile_content_list, args)
        if retval != 0:
            raise Error('command failed')

def modify_logfile(logfile, args):
    """Modify logfile, e.g. clear first or last entry."""
    entries = read_logfile(args.logfile, args.dir)
    if entries:
        if args.clear_first:
            del entries[0]
        if args.clear_last:
            del entries[-1]
        write_logfile(logfile, entries)

def dump_logfile(logfile, dirpath, end='\0'):
    """Dump logfile to stdout."""
    for entry in read_logfile(logfile, dirpath):
        if sys.version_info < (3, 0):
            entry = entry.decode(errors='replace')
            end = end.decode()
        print(entry, end=end)

def clear_logfile(logfile):
    """Remove logfile if it exists."""
    try:
        os.unlink(logfile)
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            raise Error('error removing logfile {}: {}'.format(logfile, exc.strerror))

def logfile_path(dirpath):
    """Generate default logfile path, migrating old formats and creating needed directories."""
    logdir_default = '~' + os.path.sep + '.choose_next'
    logdir = os.getenv('CHOOSE_NEXT_LOGDIR', logdir_default)
    logdir = os.path.expanduser(logdir)
    try:
        MAKEDIRS(logdir, exist_ok=True)
    except OSError as exc:
        raise Error('error creating logdir {}: {}'.format(logdir, exc.strerror))
    logfile = os.path.join(logdir, quote_plus(dirpath))
    # Migrate from old logfile name:
    old_logfile = os.path.join(logdir, dirpath.replace(os.path.sep, '_'))
    if os.path.exists(old_logfile) and not os.path.exists(logfile):
        os.rename(old_logfile, logfile)
    return logfile

def loglevel(args):
    """Return logging level."""
    levels = [logging.CRITICAL, logging.WARNING, logging.INFO, logging.DEBUG]
    return levels[min(len(levels) - 1, args.verbosity)]

def main_throws(args=None):
    """Main function, throws exception on error."""
    # For locale-specific sorting of filenames:
    locale.setlocale(locale.LC_ALL, '')
    #
    usage = '%(prog)s [OPTION]... DIR [FILE]...'
    desc = 'Chooses a file from directory DIR (recursively) and print it\'s '\
        'name to stdout. Afterwards it is appended to a log file. Only '\
        'files which are not in log file are considered for selection.\n'\
        'Tries to choose the file which is next in lexical order in DIR.'
    #
    parser = argparse.ArgumentParser(usage=usage, description=desc)
    parser.set_defaults(verbosity=1)
    parser.set_defaults(recursive=True)
    #
    parser.add_argument('dir', metavar='DIR', help='directory to choose from')
    parser.add_argument('files', metavar='FILES', nargs='*',
                        help='prefer these files before all others')
    parser.add_argument('--version', action='version', version='%(prog)s 2.0.0')
    parser.add_argument('-c', '--command', metavar='CMD',
                        help='execute CMD on every selected file; %%s in CMD is substituted '\
                             'with the filename, otherwise it is appended to CMD')
    #
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--clear', action='store_true',
                       default=False, help='remove log file and exit')
    group.add_argument('--clear-first', action='store_true',
                       default=False, help='remove first log file entry and exit')
    group.add_argument('--clear-last', action='store_true',
                       default=False, help='remove last log file entry and exit')
    group.add_argument('--dump', action='store_true',
                       default=False, help='dump log file to stdout and exit, newline separated')
    group.add_argument('--dump0', action='store_true',
                       default=False, help='dump log file to stdout and exit, '\
                                           'null character separated')
    #
    parser.add_argument('-i', '--no-read', action='store_true',
                        default=False, help='don\'t use log file to filter selection')
    parser.add_argument('-L', '--logfile', metavar='FILE',
                        help='path of log file (default: ~/.choose_next/<dirname>)')
    parser.add_argument('-l', '--last', action='store_true',
                        default=False, help='play last played file')
    parser.add_argument('-N', '--no-recursive', dest='recursive', action='store_false',
                        help='do not scan DIR recursively')
    parser.add_argument('-d', '--include-directories', action='store_true',
                        default=False, help='also select directories')
    parser.add_argument('-n', '--number', type=int, metavar='NUM',
                        help='number of files to select (-1: infinite)')
    parser.add_argument('-p', '--prepend', action='store_true',
                        default=False, help='prepend selected filename instead of appending')
    parser.add_argument('-q', '--quiet', action='store_const', dest='verbosity',
                        const=0, help='don\'t output anything')
    parser.add_argument('-R', '--recursive', action='store_true', dest='recursive',
                        help=argparse.SUPPRESS)
    parser.add_argument('-r', '--random', action='store_true',
                        default=False, help='choose a random file from DIR')
    parser.add_argument('-v', '--verbose', action='count', dest='verbosity',
                        help='be verbose (can be used multiple times)')
    parser.add_argument('-w', '--no-write', action='store_true',
                        default=False, help='don\'t record selected files to log file')
    parser.add_argument('--exclude', metavar='PATTERN',
                        help='exclude files matching PATTERN')
    parser.add_argument('--include', metavar='PATTERN',
                        help='don\'t exclude files matching PATTERN')
    args = parser.parse_args(args)
    logging.basicConfig(level=loglevel(args), format='%(message)s')
    args.dir = os.path.realpath(args.dir)
    args.files[:] = [logfile_entry_to_path(os.path.realpath(path), args.dir) for path in args.files]
    if args.number is None:
        args.number = len(args.files) if args.files else 1
    if args.logfile is None:
        args.logfile = logfile_path(args.dir)
    if args.clear:
        clear_logfile(args.logfile)
    elif args.clear_first or args.clear_last:
        modify_logfile(args.logfile, args)
    elif args.dump:
        dump_logfile(args.logfile, args.dir, end=os.linesep)
    elif args.dump0:
        dump_logfile(args.logfile, args.dir, end='\0')
    else:
        choose_next(args)

def main(args=None):
    """Main function, exits program on error."""
    try:
        main_throws(args)
    except Error as exc:
        prog_name = os.path.basename(sys.argv[0])
        logging.critical('%s: %s', prog_name, exc)
        sys.exit(1)

if __name__ == '__main__':
    sys.exit(main())
