#!/usr/bin/env python

import distutils.core
import sys
# Importing setuptools adds some features like "setup.py develop", but
# it's optional so swallow the error if it's not there.
try:
    import setuptools
except ImportError:
    pass

distutils.core.setup(
    name='Tangery',
    version='0.1.0',
    description='Tangery Queue Server',
    author='Christian Hentschel',
    author_email='chentschel@weegoh.com',
    packages=['tangery'],
    package_dir = {'tangery': 'src'},
    scripts=['src/tangery'],
    data_files=[
        ('/etc/default', ['etc/tangery']),
        ('/etc/init.d', ['etc/tangery.ubuntu'])
    ]
)

