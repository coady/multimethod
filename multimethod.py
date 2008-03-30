"""
Multiple argument dispacthing.

Call multimethod on a variable number of types.
It returns a decorator which finds the multimethod of the same name,
creating it if necessary, and adds that function to it.  For example:

    @multimethod(*types)
    def func(*args):
        ...

'func' is now a multimethod which will delegate to the above function,
when called with arguments of the specified types.  If an exact match
can't be found, the next closest method will be called (and cached).
A function can have more than one multimethod decorator.

See tests for more example usage.
"""

import sys
from itertools import imap as map, izip as zip

class signature(tuple):
    "A tuple of types that supports partial ordering."
    __slots__ = ()
    def __le__(self, other):
        return len(self) <= len(other) and all(map(issubclass, other, self))
    def __lt__(self, other):
        return self != other and self <= other
    def __sub__(self, other):
        "Return relative distances, assuming self >= other."
        return [list(left.__mro__).index(right) for left, right in zip(self, other)]

class multimethod(dict):
    "A callable directed acyclic graph of methods."
    def __new__(cls, *types):
        "Return a decorator which will add the function."
        namespace = sys._getframe(1).f_locals
        def decorator(func):
            if isinstance(func, cls):
                self, func = func, func.last
            elif func.__name__ in namespace:
                self = namespace[func.__name__]
            else:
                self = dict.__new__(cls)
                self.__name__, self.cache = func.__name__, {}
            self[types] = self.last = func
            return self
        return decorator
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
        parents = self.parents(types)
        for key, (value, superkeys) in self.items():
            if types < key and (not parents or parents & superkeys):
                superkeys -= parents
                superkeys.add(types)
        dict.__setitem__(self, signature(types), (func, parents))
    def __delitem__(self, types):
        self.cache.clear()
        dict.__delitem__(self, types)
        for key, (value, superkeys) in self.items():
            if types in superkeys:
                dict.__setitem__(self, key, (value, self.parents(key)))
    def super(self, *types):
        "Return the next applicable method of given types."
        keys = self.parents(types)
        if keys:
            return self[min(keys, key=signature(types).__sub__)]
        raise TypeError("%s%s: no methods found" % (self.__name__, types))
    def __call__(self, *args, **kwargs):
        "Resolve and dispatch to best method."
        types = tuple(map(type, args))
        if types in self:
            func = self[types]
        elif types in self.cache:
            func = self.cache[types]
        else:
            func = self.cache[types] = self.super(*types)
        return func(*args, **kwargs)
