from setuptools import setup, find_packages
import sys, os

version = "0.5.1"

setup(
    name="routr",
    version=version,
    description="URL routing made right",
    long_description=open("README").read() + "\n\n" + open("CHANGES").read(),
    author="Andrey Popp",
    author_email="8mayday@gmail.com",
    url="http://routr.readthedocs.org/",
    license="BSD",
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    install_requires=[
        "colander >= 0.9.5",
        "WebOb >= 1.2b3",
        "schemify >= 0.1",
    ],
    include_package_data=True,
    test_suite="routr.tests",
    zip_safe=False)
