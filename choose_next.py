#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2010-2017 Johannes Weißl
# License GPLv3+:
# GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>.
# This is free software: you are free to change and redistribute it.
# There is NO WARRANTY, to the extent permitted by law.

from __future__ import print_function
import sys
import os
import re
import locale
import random
import subprocess
import fnmatch
from optparse import OptionParser, SUPPRESS_HELP

class Error(Exception):
    """Aborts program, used in test suite."""
    pass

verbosity = 1

def debug(msg, *args, **kwargs):
    v = kwargs['v'] if 'v' in kwargs else 2
    if verbosity < v:
        return
    msg = msg % args
    if sys.version_info < (3, 0):
        msg = msg.decode(errors='replace')
    print(msg, file=sys.stderr)

def error(msg, *args, **kwargs):
    msg = '%s: %s' % (prog_name, msg % args)
    raise Error(msg)

def read_dir(path, recursive=False, all_entries=False, exclude=None, include=None, include_directories=False):
    '''Return a list of paths in directory at path (recursively). If
    all_entries is not true, exclude all entries starting with a dot (.).
    '''
    lst = []
    for root, dirs, files in os.walk(path):
        paths = files
        if include_directories:
            paths += dirs
        for f in paths:
            if all_entries or not f.startswith('.'):
                abspath = os.path.join(root, f)
                if not exclude or ((not fnmatch.fnmatch(abspath, exclude)) or (include and fnmatch.fnmatch(abspath, include))):
                    lst.append(os.path.relpath(abspath, path))
        if not recursive:
            break
    return lst

def read_logfile(name):
    if not os.path.exists(name):
        return []
    f = open(name, 'r')
    lst = [line.rstrip('\n') for line in f]
    f.close()
    return lst

def write_logfile(name, lines):
    f = open(name, 'w')
    f.write(''.join([e + '\n' for e in lines]))
    f.close()

def logfile_append(name, entry, mode='a'):
    f = open(name, mode)
    f.write(entry + '\n')
    f.close()

def logfile_prepend(name, entry, logfile_content):
    lines = [entry] + logfile_content
    write_logfile(name, lines)

def shellquote(s):
    return "'" + s.replace("'", "'\\''") + "'"

numkey_regex = re.compile('(\s*[+-]?[0-9]+\.?[0-9]*\s*)(.*)')
def numkey(s):
    m = numkey_regex.match(s)
    if m:
        return float(m.group(1)), locale.strxfrm(m.group(2))
    return (0.0, locale.strxfrm(s))

def path_split_all(path):
    '''Return a list of path elements, e.g. 'a/b/..//c' -> ['a', 'c'].'''
    return os.path.normpath(path).split(os.sep)

def numkey_path(path):
    return tuple(numkey(s) for s in path_split_all(path))

def choose_next(dir, logfile, options, next_file=None):

    logfile_content_list = [os.path.relpath(l, dir) if os.path.isabs(l) else l for l in read_logfile(logfile)]
    logfile_content = set(logfile_content_list)
    played_list = logfile_content_list if not options.no_read else []

    played = set(played_list)
    available = set(read_dir(dir, recursive=options.recursive, exclude=options.exclude, include=options.include, include_directories=options.include_directories))
    available_list = list(available)
    available_list.sort(key=numkey_path)
    remaining = available - played

    rewrite_logfile = False
    if not remaining:
        rewrite_logfile = True
        remaining = available

    remaining_list = list(remaining)
    remaining_list.sort(key=numkey_path)

    debug('directory to choose from: %s', dir)
    debug('logfile: %s', logfile)
    debug('files available: %d', len(available))
    for f in available_list:
        debug('%s', f, v=3)
    debug('files in logfile: %d', len(played))
    for f in played_list:
        debug('%s', f, v=3)
    debug('files remaining for selection: %d', len(remaining))
    for f in remaining_list:
        debug('%s', f, v=3)

    if not remaining:
        error('error, no files available in %s', dir)

    if next_file:
        pass
    elif options.last and played_list:
        next_file = played_list[-1]
    elif options.random:
        next_file = random.choice(remaining_list)
    else:
        x = 0
        if played_list:
            last_file = played_list[-1]
            debug('last selected file: %s', last_file)
            if last_file in available:
                x = available_list.index(last_file) + 1
                if x == len(available_list):
                    x = 0
        for i in range(x, len(available_list)) + range(0, x):
            next_file = available_list[i]
            if next_file in remaining:
                break

    debug('selected file: %s', next_file)
    next_file_abs = os.path.join(dir, next_file)

    retval = 0
    if options.command:
        next_file_quoted = shellquote(next_file_abs)
        try:
            command = options.command % next_file_quoted
        except TypeError:
            command = options.command + ' ' + next_file_quoted
        debug('executing command: %s', command)
        retval = subprocess.call(command, shell=True)

    if verbosity > 0:
        msg = next_file_abs
        if sys.version_info < (3, 0):
            msg = msg.decode(errors='replace')
        print(msg)

    if retval == 0 and not options.no_write:
        if rewrite_logfile:
            debug('truncating logfile (was full)')
        if next_file not in logfile_content or rewrite_logfile:
            if options.prepend:
                lines = logfile_content_list if not rewrite_logfile else []
                logfile_prepend(logfile, next_file, lines)
            else:
                mode = 'a' if not rewrite_logfile else 'w'
                logfile_append(logfile, next_file, mode=mode)

    return retval

def main_throws(args=None):

    global prog_name
    global verbosity

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
    parser.set_defaults(verbosity=verbosity)
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
        help='path of log file (default: %s)' % os.path.join(logdir_default,
        '${DIR//%s/_}' % (os.path.sep.replace('/', '\\/'))))
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
    verbosity = options.verbosity
    prog_name = parser.get_prog_name()
    if not args:
        error('error, no directory specified\n'\
                'Try `%s --help\' for more information.', prog_name)
    dir = args[0]

    if not os.path.exists(dir):
        error('error, directory `%s\' doesn\'t exist', dir)

    if not os.path.isdir(dir):
        error('error, `%s\' is no directory', dir)

    dir = os.path.realpath(dir)
    next_files = [os.path.relpath(f, dir) for f in args[1:]]

    if options.logfile:
        logfile = options.logfile
    else:
        logdir = os.path.expanduser(logdir)
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        logfile = os.path.join(logdir, dir.replace(os.path.sep, '_'))

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
            for l in lines:
                if sys.version_info < (3, 0):
                    l = l.decode(errors='replace')
                print(l)
        return 0

    if options.number >= 0 and options.number <= len(next_files):
        options.number = len(next_files)

    i = 0
    while True:
        next_file = next_files[i] if i < len(next_files) else None
        retval = choose_next(dir, logfile, options, next_file)
        if retval != 0:
            raise Error('command failed')
        i += 1
        if options.number >= 0 and i >= options.number:
            break

    return 0

def main(args=None):
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
