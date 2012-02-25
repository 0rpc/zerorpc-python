from setuptools import setup

setup(
    name         = 'zerorpc',
    version      = '0.1.0',
    author       = 'dotCloud inc. <team@dotcloud.com>',
    package_dir  = {'zerorpc': '.'},
    packages     = ['zerorpc'],
    zip_safe     = False,
    scripts      = [
            'bin/zerorpc-client'
        ]
    )
