About Multimethod
==================
Multiple argument dispatching.

Call *multimethod* on a variable number of types.
It returns a decorator which finds the multimethod of the same name, creating it if necessary, and adds that function to it.
For example::

   @multimethod(*types)
   def func(*args):
      pass

``func`` is now a multimethod which will delegate to the above function, when called with arguments of the specified types.
If an exact match can't be found, the next closest method is called (and cached).

If ``strict`` mode is enabled, and there are multiple candidate methods, a TypeError is raised.
A function can have more than one multimethod decorator.
Keyword arguments can be used when calling, but won't affect the dispatching.

The ``functools.singledispatch`` style syntax introduced in Python 3.4 is also supported.
::

   @multidispatch
   def func(*args):
      pass

   @func.register(*types):
   def _(*args):
      pass

See tests for more example usage.

Installation
==================
Standard installation from pypi or local download.
::

   pip install multimethod
   python setup.py install

Dependencies
==================
Python 2.7 or 3.2+.

Tests
==================
100% branch coverage.
::

   py.test

Changes:
==================
0.4

   * Dispatch on Python 3 annotations

0.5

   * Optimized dispatching
   * Support for ``functools.singledispatch`` syntax
