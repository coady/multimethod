from setuptools import setup
import multimethod

setup(
    name='multimethod',
    version=multimethod.__version__,
    description='Multiple argument dispatching.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Aric Coady',
    author_email='aric.coady@gmail.com',
    url='https://bitbucket.org/coady/multimethod',
    license='Apache Software License',
    py_modules=['multimethod'],
    python_requires='>=2.7',
    tests_require=['pytest-cov'],
    keywords='multiple dispatch multidispatch generic functions methods overload',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
