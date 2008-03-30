from distutils.core import setup

setup(
    name='multimethod',
    version='0.1',
    description='Multiple argument dispacthing.',
    long_description='''
    Multimethod is a simple pure python 2.5 module for dispatching functions on the types of multiple arguments.
    It supports resolving to the next applicable method (super) and caching for fast dispatch.
    It has more features than simplegeneric, but is lighter weight than PEAK.
    ''',
    author='Aric Coady',
    author_email='aric.coady@gmail.com',
    py_modules=['multimethod'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Python Software Foundation License',
    ],
)
