#!/usr/bin/env python

from distutils.core import setup

setup(
    name='OpenFL',
    description='API for the Form 1(+) SLA 3D printer',
    url='https://github.com/Formlabs/OpenFL',
    author='Formlabs',
    author_email='openfl@formlabs.com',
    classifiers = [
        'Programming Language :: Python',
        'Development Status :: 2 - Pre-Alpha',
    ],
    packages=['OpenFL'],
    install_requires=['pyusb >= 1.0.0rc1', 'enum34', 'numpy', 'scipy']
)
