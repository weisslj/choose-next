# -*- coding: utf-8 -*-

"""A setuptools based setup module."""

from __future__ import unicode_literals
import os
import codecs
from setuptools import setup

# Get the long description from the README file
HERE = os.path.abspath(os.path.dirname(__file__))
with codecs.open(os.path.join(HERE, 'README.rst'), encoding='utf-8') as stream:
    LONG_DESCRIPTION = '\n'.join(stream.read().split('\n')[5:])

setup(
    name='choose-next',
    version='3.0.0',
    description='Chooses a file from a directory. Very handy to re-watch tv series!',
    long_description=LONG_DESCRIPTION,
    author='Johannes Weißl',
    author_email='jargon@molb.org',
    url='https://github.com/weisslj/choose-next',
    license='GPLv3+',
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Operating System :: POSIX',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Utilities',
    ],
    py_modules=[
        'choose_next',
    ],
    entry_points={
        'console_scripts': [
            'choose-next=choose_next:main',
        ],
    },
    test_suite='test_choose_next',
    python_requires='>=3.6',
)
