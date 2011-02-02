#!/usr/bin/env python

from setuptools import setup,find_packages

setup(
    name='Hammertime',
    version='0.1.2',

    description='Time tracking with git.',
    long_description=open('README.md').read(),
    keywords='git time tracking',
    url='https://github.com/caffeinehit/hammertime',
    author='Alen Mujezinovic',
    author_email='alen@caffeinehit.com',
    license='MIT',

    packages=find_packages(),
    include_package_data=True,

    entry_points = {
        'console_scripts': [
            'git-time = hammertime:main',
        ],
    },
    install_requires = [
        'simplejson == 2.1.1',
        'GitPython >= 0.3.0'
    ],

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development',
    ],
)
