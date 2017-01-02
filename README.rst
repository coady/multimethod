.. image:: https://img.shields.io/pypi/v/multimethod.svg
   :target: https://pypi.python.org/pypi/multimethod/
.. image:: https://img.shields.io/pypi/pyversions/multimethod.svg
.. image:: https://img.shields.io/pypi/status/multimethod.svg
.. image:: https://img.shields.io/travis/coady/multimethod.svg
   :target: https://travis-ci.org/coady/multimethod
.. image:: https://img.shields.io/codecov/c/github/coady/multimethod.svg
   :target: https://codecov.io/github/coady/multimethod

Multimethod provides a decorator for adding multiple argument dispatching to functions.
The decorator finds the multimethod of the same name, creating it if necessary, and registers the function with its annotations.

There are several multiple dispatch libraries on PyPI.  This one aims to be correct, simple, and fast.
It doesn't support arbitrary predicates, for example, but should be the fastest pure Python implementation possible.

Usage
==================
.. code-block:: python

   from multimethod import multimethod

   @multimethod
   def func(x: int, y: float):
      ...

``func`` is now a ``multimethod`` which will delegate to the above function, when called with arguments of the specified types.
Subsequent usage will register new types and functions to the existing multimethod of the same name.
If an exact match can't be found, the next closest method is called (and cached).
Candidate methods are ranked based on their subclass relationships.
If no matches are found, a custom ``TypeError`` is raised.

A ``strict`` flag can also be set on the ``multimethod`` object,
in which case finding multiple matches also raises a ``TypeError``.
Keyword arguments can be used when calling, but won't affect the dispatching.

Types can instead be specified by calling ``multimethod``, thereby supporting Python 2 as well.
This syntax also supports stacking decorators for registering multiple signatures.

.. code-block:: python

   @multimethod(int, float)
   @multimethod(float, int)
   def func(x, y):
      ...

The ``functools.singledispatch`` style syntax introduced in Python 3.4 is also supported.
This requires creating a ``multimethod`` explicitly, and consequently doesn't rely on the name matching.

.. code-block:: python

   from multimethod import multidispatch

   @multidispatch
   def func(*args):
      ...

   @func.register(*types)
   def _(*args):
      ...

See tests for more example usage.

Installation
==================
::

   $ pip install multimethod

Dependencies
==================
* Python 2.7, 3.3+

Tests
==================
100% branch coverage. ::

   $ pytest [--cov]

Changes
==================
0.6

* Multimethods can be defined inside a class

0.5

* Optimized dispatching
* Support for ``functools.singledispatch`` syntax

0.4

* Dispatch on Python 3 annotations
