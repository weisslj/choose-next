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
from optparse import OptionParser, SUPPRESS_HELP
from itertools import islice, cycle

if sys.version_info < (3, 0):
    from itertools import ifilter as filter  # pylint: disable=redefined-builtin
if sys.version_info < (3, 2):
    os.fsencode = lambda filename: filename

class Error(Exception):
    """Abort program, used in test suite."""
    pass

def debug(do_show, msg, *args, **kwargs):
    """Output debug message to stderr."""
    if not do_show:
        return
    msg = msg.format(*args, **kwargs)
    if sys.version_info < (3, 0):
        msg = msg.decode(errors='replace')
    print(msg, file=sys.stderr)

def error(msg, *args, **kwargs):
    """Raise Error exception."""
    prog_name = os.path.basename(sys.argv[0])
    msg = '{}: {}'.format(prog_name, msg.format(*args, **kwargs))
    raise Error(msg)

def read_dir(path, recursive=False, exclude=None, include=None, include_directories=False):
    """Return a list of paths in directory at path (recursively)."""
    paths = []
    for root, dirs, files in os.walk(path):
        names = files
        if include_directories:
            names += dirs
        for name in names:
            if not name.startswith('.'):
                abspath = os.path.join(root, name)
                if not exclude or \
                        ((not fnmatch.fnmatch(abspath, exclude)) or \
                        (include and fnmatch.fnmatch(abspath, include))):
                    paths.append(os.path.relpath(abspath, path))
        if not recursive:
            break
    return paths

def read_logfile(path):
    """Return list of logfile entries."""
    try:
        with open(path, 'r') as stream:
            return [line.rstrip('\r\n') for line in stream]
    except IOError as exc:
        if exc.errno == errno.ENOENT:
            return []
        else:
            raise Error('error reading logfile: {}'.format(exc.strerror))

def write_logfile(path, entries):
    """Write logfile entries to path."""
    with open(path, 'wb') as stream:
        stream.write(b''.join([os.fsencode(e) + os.linesep.encode() for e in entries]))

def logfile_append(path, entry, mode='ab'):
    """Append logfile entry to path or rewrite."""
    with open(path, mode) as stream:
        stream.write(os.fsencode(entry) + os.linesep.encode())

def logfile_prepend(path, entry, old_entries):
    """Prepend logfile entry to path."""
    entries = [entry] + old_entries
    write_logfile(path, entries)

def shellquote(string):
    """Return a quoted version of string suitable for a sh-like shell."""
    return "'" + string.replace("'", "'\\''") + "'"

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

def choose_next(directory, logfile, options, next_file=None):
    """Main functionality."""
    logfile_content_list = [os.path.relpath(l, directory) if os.path.isabs(l) else l
                            for l in read_logfile(logfile)]
    logfile_content = set(logfile_content_list)
    played_list = logfile_content_list if not options.no_read else []

    played = set(played_list)
    available = set(read_dir(directory, recursive=options.recursive, exclude=options.exclude,
                             include=options.include,
                             include_directories=options.include_directories))
    available_list = list(available)
    available_list.sort(key=numkey_path)
    remaining = available - played

    rewrite_logfile = False
    if not remaining:
        rewrite_logfile = True
        remaining = available

    remaining_list = list(remaining)
    remaining_list.sort(key=numkey_path)

    debug(options.verbosity > 1, 'directory to choose from: {}', directory)
    debug(options.verbosity > 1, 'logfile: {}', logfile)
    debug(options.verbosity > 1, 'files available: {}', len(available))
    for path in available_list:
        debug(options.verbosity > 2, '{}', path)
    debug(options.verbosity > 1, 'files in logfile: {}', len(played))
    for path in played_list:
        debug(options.verbosity > 2, '{}', path)
    debug(options.verbosity > 1, 'files remaining for selection: {}', len(remaining))
    for path in remaining_list:
        debug(options.verbosity > 2, '{}', path)

    if not remaining:
        error('error, no files available in {}', directory)

    if next_file:
        pass
    elif options.last and played_list:
        next_file = played_list[-1]
    elif options.random:
        next_file = random.choice(remaining_list)
    else:
        index = 0
        if played_list:
            last_file = played_list[-1]
            debug(options.verbosity > 1, 'last selected file: {}', last_file)
            if last_file in available:
                index = available_list.index(last_file) + 1
        next_file = next(filter(lambda path: path in remaining,
                                islice(cycle(available_list), index, None)))

    debug(options.verbosity > 1, 'selected file: {}', next_file)
    next_file_abs = os.path.join(directory, next_file)

    retval = 0
    if options.command:
        next_file_quoted = shellquote(next_file_abs)
        try:
            command = options.command % next_file_quoted
        except TypeError:
            command = options.command + ' ' + next_file_quoted
        debug(options.verbosity > 1, 'executing command: {}', command)
        retval = subprocess.call(command, shell=True)

    if options.verbosity > 0:
        msg = next_file_abs
        if sys.version_info < (3, 0):
            msg = msg.decode(errors='replace')
        print(msg)

    if retval == 0 and not options.no_write:
        if rewrite_logfile:
            debug(options.verbosity > 1, 'truncating logfile (was full)')
        if next_file not in logfile_content or rewrite_logfile:
            if options.prepend:
                lines = logfile_content_list if not rewrite_logfile else []
                logfile_prepend(logfile, next_file, lines)
            else:
                mode = 'ab' if not rewrite_logfile else 'wb'
                logfile_append(logfile, next_file, mode=mode)

    return retval

def main_throws(args=None):
    """Main function, throws exception on error."""
    # For locale-specific sorting of filenames:
    locale.setlocale(locale.LC_ALL, '')

    usage = 'usage: %prog [OPTION]... DIR [FILE]...'
    version = '%prog 1.1'
    desc = 'Chooses a file from directory DIR (recursively) and print it\'s '\
        'name to stdout. Afterwards it is appended to a log file. Only '\
        'files which are not in log file are considered for selection.\n'\
        'Tries to choose the file which is next in lexical order in DIR.'

    logdir_default = '~' + os.path.sep + '.choose_next'
    logdir = os.getenv('CHOOSE_NEXT_LOGDIR', logdir_default)

    parser = OptionParser(usage=usage, version=version, description=desc)
    parser.set_defaults(verbosity=1)
    parser.set_defaults(recursive=True)

    parser.add_option('-c', '--command', metavar='CMD',
                      help='execute CMD on every selected file; %s in CMD is substituted '\
                           'with the filename, otherwise it is appended to CMD')

    parser.add_option('--clear', action='store_true',
                      default=False, help='remove log file and exit')
    parser.add_option('--clear-first', action='store_true',
                      default=False, help='remove first log file entry and exit')
    parser.add_option('--clear-last', action='store_true',
                      default=False, help='remove last log file entry and exit')

    parser.add_option('--dump', action='store_true',
                      default=False, help='dump log file to stdout and exit')

    parser.add_option('-i', '--no-read', action='store_true',
                      default=False, help='don\'t use log file to filter selection')
    parser.add_option('-L', '--logfile', metavar='FILE',
                      help='path of log file (default: ~/.choose_next/<dirname>)')
    parser.add_option('-l', '--last', action='store_true',
                      default=False, help='play last played file')
    parser.add_option('-N', '--no-recursive', dest='recursive', action='store_false',
                      help='do not scan DIR recursively')
    parser.add_option('-d', '--include-directories', action='store_true',
                      default=False, help='also select directories')
    parser.add_option('-n', '--number', type='int', default=1, metavar='NUM',
                      help='number of files to select (-1: infinite)')
    parser.add_option('-p', '--prepend', action='store_true',
                      default=False, help='prepend selected filename instead of appending')
    parser.add_option('-q', '--quiet', action='store_const', dest='verbosity',
                      const=0, help='don\'t output anything')
    parser.add_option('-R', '--recursive', action='store_true', dest='recursive',
                      help=SUPPRESS_HELP)
    parser.add_option('-r', '--random', action='store_true',
                      default=False, help='choose a random file from DIR')
    parser.add_option('-v', '--verbose', action='count', dest='verbosity',
                      help='be verbose (can be used multiple times)')
    parser.add_option('-w', '--no-write', action='store_true',
                      default=False, help='don\'t record selected files to log file')
    parser.add_option('--exclude', metavar='PATTERN',
                      help='exclude files matching PATTERN')
    parser.add_option('--include', metavar='PATTERN',
                      help='don\'t exclude files matching PATTERN')

    (options, args) = parser.parse_args(args)
    if not args:
        error('error, no directory specified\n'\
                'Try `{} --help\' for more information.', parser.get_prog_name())
    directory = args[0]

    if not os.path.exists(directory):
        error('error, directory `{}\' doesn\'t exist', directory)

    if not os.path.isdir(directory):
        error('error, `{}\' is no directory', directory)

    directory = os.path.realpath(directory)
    next_files = [os.path.relpath(f, directory) for f in args[1:]]

    if options.logfile:
        logfile = options.logfile
    else:
        logdir = os.path.expanduser(logdir)
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        logfile = os.path.join(logdir, directory.replace(os.path.sep, '_'))

    if options.clear:
        if os.path.exists(logfile):
            os.unlink(logfile)
        return 0

    if options.clear_first or options.clear_last or options.dump:
        lines = read_logfile(logfile)
        if lines and options.clear_first:
            del lines[0]
        if lines and options.clear_last:
            del lines[-1]
        if options.clear_first or options.clear_last:
            write_logfile(logfile, lines)
        if options.dump:
            for line in lines:
                if sys.version_info < (3, 0):
                    line = line.decode(errors='replace')
                print(line)
        return 0

    if options.number >= 0 and options.number <= len(next_files):
        options.number = len(next_files)

    i = 0
    while True:
        next_file = next_files[i] if i < len(next_files) else None
        retval = choose_next(directory, logfile, options, next_file)
        if retval != 0:
            raise Error('command failed')
        i += 1
        if options.number >= 0 and i >= options.number:
            break

    return 0

def main(args=None):
    """Main function, exits program on error."""
    try:
        main_throws(args)
    except Error as exc:
        msg = str(exc)
        if sys.version_info < (3, 0):
            msg = msg.decode(errors='replace')  # pylint: disable=redefined-variable-type
        print(msg, file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    sys.exit(main())
