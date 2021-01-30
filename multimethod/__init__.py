import abc
import collections
import functools
import inspect
import itertools
import types
import typing
from typing import Callable, Iterable, Iterator, Mapping, Union

__version__ = '1.5'


def groupby(func: Callable, values: Iterable) -> dict:
    """Return mapping of key function to values."""
    groups = collections.defaultdict(list)  # type: dict
    for value in values:
        groups[func(value)].append(value)
    return groups


def get_types(func: Callable) -> tuple:
    """Return evaluated type hints for positional required parameters in order."""
    if not hasattr(func, '__annotations__'):
        return ()
    type_hints = typing.get_type_hints(func)
    positionals = {inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD}
    annotations = [
        type_hints.get(param.name, object)
        for param in inspect.signature(func).parameters.values()
        if param.default is param.empty and param.kind in positionals
    ]  # missing annotations are padded with `object`, but trailing objects are unnecessary
    return tuple(itertools.dropwhile(lambda cls: cls is object, reversed(annotations)))[::-1]


class DispatchError(TypeError):
    pass


class subtype(type):
    """A normalized generic type which checks subscripts."""

    __origin__: type
    __args__: tuple

    def __new__(cls, tp, *args):
        if tp is typing.Any:
            return object
        if isinstance(tp, typing.TypeVar):
            if not tp.__constraints__:
                return object
            tp = typing.Union[tp.__constraints__]
        origin = getattr(tp, '__extra__', getattr(tp, '__origin__', tp))
        args = tuple(map(cls, getattr(tp, '__args__', None) or args))
        if set(args) <= {object} and not (origin is tuple and args):
            return origin
        bases = (origin,) if type(origin) is type else ()
        namespace = {'__origin__': origin, '__args__': args}
        return type.__new__(cls, str(tp), bases, namespace)

    def __init__(self, tp, *args):
        if isinstance(self.__origin__, abc.ABCMeta):
            self.__origin__.register(self)

    def __getstate__(self) -> tuple:
        return self.__origin__, self.__args__

    def __eq__(self, other) -> bool:
        return isinstance(other, subtype) and self.__getstate__() == other.__getstate__()

    def __hash__(self) -> int:
        return hash(self.__getstate__())

    def __subclasscheck__(self, subclass: type) -> bool:
        origin = getattr(subclass, '__extra__', getattr(subclass, '__origin__', subclass))
        args = getattr(subclass, '__args__', ())
        if origin is typing.Union:
            return all(issubclass(cls, self) for cls in args)
        if self.__origin__ is typing.Union:
            return issubclass(subclass, self.__args__)
        nargs = len(self.__args__)
        if self.__origin__ is tuple and self.__args__[-1:] == (Ellipsis,):
            nargs -= 1
            args = args[:nargs]
        return (  # check args first to avoid a recursion error in ABCMeta
            len(args) == nargs
            and issubclass(origin, self.__origin__)
            and all(map(issubclass, args, self.__args__))
        )

    @classmethod
    def subcheck(cls, tp: type) -> bool:
        """Return whether type requires checking subscripts using `get_type`."""
        return isinstance(tp, cls) and (
            tp.__origin__ is not Union or any(map(cls.subcheck, tp.__args__))
        )


def distance(cls, subclass: type) -> int:
    """Return estimated distance between classes for tie-breaking."""
    if getattr(cls, '__origin__', None) is typing.Union:
        return min(distance(arg, subclass) for arg in cls.__args__)
    mro = type.mro(subclass)
    return mro.index(cls if cls in mro else object)


class signature(tuple):
    """A tuple of types that supports partial ordering."""

    parents: set

    def __new__(cls, types: Iterable):
        return tuple.__new__(cls, map(subtype, types))

    def __le__(self, other) -> bool:
        return len(self) <= len(other) and all(map(issubclass, other, self))

    def __lt__(self, other) -> bool:
        return self != other and self <= other

    def __sub__(self, other) -> tuple:
        """Return relative distances, assuming self >= other."""
        return tuple(map(distance, other, self))


class multimethod(dict):
    """A callable directed acyclic graph of methods."""

    pending: set

    def __new__(cls, func):
        namespace = inspect.currentframe().f_back.f_locals
        self = functools.update_wrapper(dict.__new__(cls), func)
        self.pending = set()
        self.get_type = type  # default type checker
        homonym = namespace.get(func.__name__, self)
        return homonym if isinstance(homonym, multimethod) else self

    def __init__(self, func: Callable):
        try:
            self[get_types(func)] = func
        except (NameError, AttributeError):
            self.pending.add(func)

    def register(self, *args) -> Callable:
        """Decorator for registering a function.

        Optionally call with types to return a decorator for unannotated functions.
        """
        if len(args) == 1 and hasattr(args[0], '__annotations__'):
            return overload.register(self, *args)  # type: ignore
        return lambda func: self.__setitem__(args, func) or func

    def __get__(self, instance, owner):
        return self if instance is None else types.MethodType(self, instance)

    def parents(self, types: tuple) -> set:
        """Find immediate parents of potential key."""
        parents = {key for key in self if isinstance(key, signature) and key < types}
        return parents - {ancestor for parent in parents for ancestor in parent.parents}

    def clean(self):
        """Empty the cache."""
        for key in list(self):
            if not isinstance(key, signature):
                super().__delitem__(key)

    def copy(self):
        """Return a new multimethod with the same methods."""
        other = dict.__new__(type(self))
        other.update(self)
        return other

    def __setitem__(self, types: tuple, func: Callable):
        self.clean()
        types = signature(types)
        parents = types.parents = self.parents(types)
        for key in self:
            if types < key and (not parents or parents & key.parents):
                key.parents -= parents
                key.parents.add(types)
        if any(map(subtype.subcheck, types)):
            self.get_type = get_type  # switch to slower generic type checker
        super().__setitem__(types, func)
        self.__doc__ = self.docstring

    def __delitem__(self, types: tuple):
        self.clean()
        super().__delitem__(types)
        for key in self:
            if types in key.parents:
                key.parents = self.parents(key)
        self.__doc__ = self.docstring

    def __missing__(self, types: tuple) -> Callable:
        """Find and cache the next applicable method of given types."""
        self.evaluate()
        if types in self:
            return self[types]
        groups = groupby(signature(types).__sub__, self.parents(types))
        keys = groups[min(groups)] if groups else []
        funcs = {self[key] for key in keys}
        if len(funcs) == 1:
            return self.setdefault(types, *funcs)
        msg = f"{self.__name__}: {len(keys)} methods found"  # type: ignore
        raise DispatchError(msg, types, keys)

    def __call__(self, *args, **kwargs):
        """Resolve and dispatch to best method."""
        return self[tuple(map(self.get_type, args))](*args, **kwargs)

    def evaluate(self):
        """Evaluate any pending forward references.

        This can be called explicitly when using forward references,
        otherwise cache misses will evaluate.
        """
        while self.pending:
            func = self.pending.pop()
            self[get_types(func)] = func

    @property
    def docstring(self):
        """a descriptive docstring of all registered functions"""
        docs = []
        for func in set(self.values()):
            try:
                sig = inspect.signature(func)
            except ValueError:
                sig = ''
            doc = func.__doc__ or ''
            docs.append(f'{func.__name__}{sig}\n    {doc}')
        return '\n\n'.join(docs)


class multidispatch(multimethod):
    """Provisional wrapper for future compatibility with `functools.singledispatch`."""


get_type = multimethod(type)
get_type.__doc__ = """Return a generic `subtype` which checks subscripts."""
for atomic in (Iterator, str, bytes):
    get_type[(atomic,)] = type


@multimethod  # type: ignore[no-redef]
def get_type(arg: tuple):
    """Return generic type checking all values."""
    return subtype(type(arg), *map(get_type, arg))


@multimethod  # type: ignore[no-redef]
def get_type(arg: Mapping):
    """Return generic type checking first item."""
    return subtype(type(arg), *map(get_type, next(iter(arg.items()), ())))


@multimethod  # type: ignore[no-redef]
def get_type(arg: Iterable):
    """Return generic type checking first value."""
    return subtype(type(arg), *map(get_type, itertools.islice(arg, 1)))


def isa(*types: type) -> Callable:
    """Partially bound `isinstance`."""
    return lambda arg: isinstance(arg, types)


class overload(collections.OrderedDict):
    """Ordered functions which dispatch based on their annotated predicates."""

    __get__ = multimethod.__get__

    def __new__(cls, func):
        namespace = inspect.currentframe().f_back.f_locals
        self = functools.update_wrapper(super().__new__(cls), func)
        return namespace.get(func.__name__, self)

    def __init__(self, func: Callable):
        self[inspect.signature(func)] = func

    def __call__(self, *args, **kwargs):
        """Dispatch to first matching function."""
        for sig, func in reversed(self.items()):
            arguments = sig.bind(*args, **kwargs).arguments
            if all(
                param.annotation(arguments[name])
                for name, param in sig.parameters.items()
                if param.annotation is not param.empty
            ):
                return func(*args, **kwargs)
        raise DispatchError("No matching functions found")

    def register(self, func: Callable) -> Callable:
        """Decorator for registering a function."""
        self.__init__(func)  # type: ignore
        return self if self.__name__ == func.__name__ else func  # type: ignore


class multimeta(type):
    """Convert all callables in namespace to multimethods."""

    class __prepare__(dict):
        def __init__(*args):
            pass

        def __setitem__(self, key, value):
            if callable(value):
                value = getattr(self.get(key), 'register', multimethod)(value)
            super().__setitem__(key, value)
