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
    url='http://github.com/weisslj/choose-next',
    license='GNU GPL v3',
    classifiers=[
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python :: 2.5',
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
