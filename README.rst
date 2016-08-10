.. image:: https://img.shields.io/pypi/v/multimethod.svg
   :target: https://pypi.python.org/pypi/multimethod/
.. image:: https://img.shields.io/pypi/pyversions/multimethod.svg
.. image:: https://img.shields.io/pypi/status/multimethod.svg
.. image:: https://img.shields.io/travis/coady/multimethod.svg
   :target: https://travis-ci.org/coady/multimethod
.. image:: https://img.shields.io/codecov/c/github/coady/multimethod.svg
   :target: https://codecov.io/github/coady/multimethod

Call ``multimethod`` on a variable number of types.
It returns a decorator which finds the multimethod of the same name, creating it if necessary, and adds that function to it.

.. code-block:: python

   @multimethod(*types)
   def func(*args):
      pass

``func`` is now a multimethod which will delegate to the above function, when called with arguments of the specified types.
If an exact match can't be found, the next closest method is called (and cached).

If ``strict`` mode is enabled, and there are multiple candidate methods, a TypeError is raised.
A function can have more than one multimethod decorator.
Keyword arguments can be used when calling, but won't affect the dispatching.

The ``functools.singledispatch`` style syntax introduced in Python 3.4 is also supported.

.. code-block:: python

   @multidispatch
   def func(*args):
      pass

   @func.register(*types)
   def _(*args):
      pass

See tests for more example usage.

Installation
==================
::

   $ pip install multimethod

Dependencies
==================
Python 2.7 or 3.3+.

Tests
==================
100% branch coverage. ::

   $ py.test [--cov]

Changes
==================
0.5

   * Optimized dispatching
   * Support for ``functools.singledispatch`` syntax

0.4

   * Dispatch on Python 3 annotations
