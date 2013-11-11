"""
**Multiple argument dispatching**

Call *multimethod* on a variable number of types.
It returns a decorator which finds the multimethod of the same name, creating it if necessary, and adds that function to it.
For example::

    @multimethod(*types)
    def func(*args):
        pass

|

*func* is now a multimethod which will delegate to the above function, when called with arguments of the specified types.
If an exact match can't be found, the next closest method is called (and cached).
If *strict* is enabled, and there are multiple candidate methods, a TypeError is raised.
A function can have more than one multimethod decorator.

See tests for more example usage.
Supported on Python 2.6 or higher, including Python 3.

Changes in 0.4:
 * Dispatch on python 3 annotations
"""

import sys
try:
    from future_builtins import map, zip
except ImportError:
    pass

__version__ = '0.4'

class DispatchError(TypeError):
    pass

class signature(tuple):
    "A tuple of types that supports partial ordering."
    __slots__ = ()
    def __le__(self, other):
        return len(self) <= len(other) and all(map(issubclass, other, self))
    def __lt__(self, other):
        return self != other and self <= other
    def __sub__(self, other):
        "Return relative distances, assuming self >= other."
        return [left.__mro__.index(right if right in left.__mro__ else object) for left, right in zip(self, other)]

class multimethod(dict):
    "A callable directed acyclic graph of methods."
    @classmethod
    def new(cls, name='', strict=False):
        "Explicitly create a new multimethod.  Assign to local name in order to use decorator."
        self = dict.__new__(cls)
        self.__name__, self.strict, self.cache = name, strict, {}
        return self
    def __new__(cls, *types):
        "Return a decorator which will add the function."
        namespace = sys._getframe(1).f_locals
        def decorator(func):
            if isinstance(func, cls):
                self, func = func, func.last
            else:
                self = namespace.get(func.__name__, cls.new(func.__name__))
            self[types] = self.last = func
            return self
        if len(types) == 1 and hasattr(types[0], '__annotations__'):
            func, = types
            types = tuple(map(func.__annotations__.__getitem__, func.__code__.co_varnames[:len(func.__annotations__)]))
            return decorator(func)
        return decorator
    def __init__(self, *types):
        dict.__init__(self)
    def parents(self, types):
        "Find immediate parents of potential key."
        parents, ancestors = set(), set()
        for key, (value, superkeys) in self.items():
            if key < types:
                parents.add(key)
                ancestors |= superkeys
        return parents - ancestors
    def __getitem__(self, types):
        return dict.__getitem__(self, types)[0]
    def __setitem__(self, types, func):
        self.cache.clear()
        types = signature(types)
        parents = self.parents(types)
        for key, (value, superkeys) in self.items():
            if types < key and (not parents or parents & superkeys):
                superkeys -= parents
                superkeys.add(types)
        dict.__setitem__(self, types, (func, parents))
    def __delitem__(self, types):
        self.cache.clear()
        dict.__delitem__(self, types)
        for key, (value, superkeys) in self.items():
            if types in superkeys:
                dict.__setitem__(self, key, (value, self.parents(key)))
    def super(self, *types):
        "Return the next applicable method of given types."
        types = signature(types)
        keys = self.parents(types)
        if keys and (len(keys) == 1 or not self.strict):
            return self[min(keys, key=types.__sub__)]
        raise DispatchError("{0}{1}: {2} methods found".format(self.__name__, types, len(keys)))
    def __call__(self, *args, **kwargs):
        "Resolve and dispatch to best method."
        types = tuple(map(type, args))
        try:
            func = self.cache[types]
        except KeyError:
            func = self.cache[types] = self[types] if types in self else self.super(*types)
        return func(*args, **kwargs)
