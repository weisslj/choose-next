# -*- coding: utf-8 -*-

"""A setuptools based setup module."""

from __future__ import unicode_literals
from setuptools import setup

setup(
    name='choose-next',
    version='1.1',
    description='Chooses a file from a directory. '\
                'Very handy to re-watch tv series!',
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
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Utilities',
    ],
    py_modules=[
        'choose_next',
    ],
    entry_points={
        'console_scripts': [
            'choose_next=choose_next:main',
        ],
    },
    test_suite='test_choose_next',
)
