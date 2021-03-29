choose-next
===========

Chooses a file from a directory. Very handy to re-watch tv series!

Motivation
----------

Sometimes all you want to do is to lie in bed and watch a few episodes. But
navigating to the right folder and choosing an episode which you haven't seen
yesterday is too much work. With this small script all you have to do is to
type "playfuturama" (using tab completion of course!) if you have set up e.g.
this alias::

  alias playfuturama='choose-next -c "mplayer -fs" "/media/usb/Futurama"'

News
----

=====  ==========  ==================================================================
3.0.0  2021-03-29  Require Python 3.6 (no new features, just usage of "try ... from")
2.0.1  2017-05-01  Small fixes, Windows compatible
2.0.0  2017-04-30  Bugfixes, Python 3 support, extensive test suite
1.1    2011-04-26  Bugfixes, ``--exclude``, ``--include``, and ``-d``
1.0    2010-04-26  First working version
=====  ==========  ==================================================================

Examples
--------

Over the next few weeks you want to watch all Futurama episodes in strict
rotation::

  # clear existing log file
  choose-next --clear /media/usb/Futurama
  # no special options needed
  alias playfuturama='choose-next -c "mplayer -fs" "/media/usb/Futurama"'

You want to see a random episode (out of order!), but not one you have already
seen. You want to prepend the filename so that the rotation order is retained::

  playfuturama -rp

You were somehow distracted, and want to watch the last episode again::

  playfuturama -l

You want to watch a specific episode, and continue to watch from this point on::

  playfuturama -n10 "/media/usb/Futurama/S04E01.avi"

Usage
-----

::

  choose-next [OPTION]... DIR [FILE]...

    DIR        directory to choose from
    FILES      prefer these files before all others

  Some options:

    -c CMD, --command=CMD      execute CMD on every selected file; %s in CMD is
                               substituted with the filename, otherwise it is
                               appended to CMD
    --clear                    remove log file and exit
    -l, --last                 play last played file
    -n NUM, --number=NUM       number of files to select (-1: infinite)
    -p, --prepend              prepend selected filename instead of appending
    -r, --random               choose a random file from DIR

Copyright
=========

| Copyright (C) 2010-2021 Johannes Weißl
| License GPLv3+:
| GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
| This is free software: you are free to change and redistribute it.
| There is NO WARRANTY, to the extent permitted by law.
