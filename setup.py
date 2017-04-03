#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup

setup(name='fbscraper',
      version='0.1',
      description='',
      url='https://github.com/elcoc0/fbscraper',
      author='elcoc0',
      author_email='elcoco@protonmail.ch',
      license='MIT',
      packages=['fbscraper'],
      entry_points={
        'console_scripts': [
            'fbscraper = fbscraper.__main__:main'
        ]

      },
      )
