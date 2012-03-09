from setuptools import setup

setup(
    name         = 'zerorpc',
    version      = '0.1.0',
    author       = 'dotCloud inc. <team@dotcloud.com>',
    package_dir  = {'zerorpc': '.'},
    packages     = ['zerorpc'],
    install_requires = [
            'argparse',
            'gevent',
            'msgpack-python',
            'pyzmq-static==2.1.7',
    ],
    zip_safe     = False,
    scripts      = [
            'bin/zerorpc-client'
        ]
    )
