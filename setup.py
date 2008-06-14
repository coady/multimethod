from distutils.core import setup

setup(
    name='multimethod',
    version='0.2',
    description='Multiple argument dispacthing.',
    long_description=open('multimethod.py').read().split('"""\n')[1],
    author='Aric Coady',
    author_email='aric.coady@gmail.com',
    py_modules=['multimethod'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Python Software Foundation License',
    ],
)
