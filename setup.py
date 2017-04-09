# -*- coding: utf-8 -*-

"""A setuptools based setup module."""

from setuptools import setup

setup(
    name='choose-next',
    version='1.1',
    description='Chooses a file from a directory. '\
                'Very handy to re-watch tv series!',
    author=u'Johannes Weißl',
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
)
