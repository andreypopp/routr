import os
import sys

from setuptools import find_packages, setup


is_py26 = sys.version_info[:2] == (2, 6)
version = '0.7.0'


setup(
    name='routr',
    version=version,
    description='URL routing made right',
    long_description=open('README').read() + '\n\n' + open('CHANGES').read(),
    author='Andrey Popp',
    author_email='8mayday@gmail.com',
    url='http://routr.readthedocs.org/',
    license='BSD',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    install_requires=list(filter(None, [
        'WebOb >= 1.2b3',
        'six >= 1.3.0',
        'unittest2 == 0.5.1' if is_py26 else None,
    ])),
    include_package_data=True,
    test_suite='routr.tests',
    zip_safe=False)
