#!/usr/bin/python

# See file COPYING distributed with sjs for copyright and license.

from distutils.core import setup

long_description = open('README.rst').read()

setup(name='sjs', 
      version='0.1.0', 
      description='A simple job scheduler', 
      author='Christian Haselgrove', 
      author_email='christian.haselgrove@umassmed.edu', 
      url='https://github.com/chaselgrove/sjs', 
      scripts=['sjs_qconf', 
               'sjs_qdel', 
               'sjs_qrun', 
               'sjs_qstat', 
               'sjs_qsub'], 
      classifiers=['Development Status :: 3 - Alpha', 
                   'Environment :: Console', 
                   'Intended Audience :: Developers', 
                   'License :: OSI Approved :: BSD License', 
                   'Operating System :: OS Independent', 
                   'Programming Language :: Python', 
                   'Topic :: Software Development :: Testing'], 
      license='BSD license', 
      long_description=long_description
     )

# eof
