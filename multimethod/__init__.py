import abc
import collections
import contextlib
import functools
import inspect
import itertools
import types
from typing import Any, Callable, Dict, Iterable, Iterator, Literal, Mapping, Optional, Tuple
from typing import TypeVar, Union, get_type_hints, no_type_check, overload as tp_overload

__version__ = '1.10'
Empty = types.new_class('*')


class DispatchError(TypeError):
    pass


class subtype(abc.ABCMeta):
    """A normalized generic type which checks subscripts.

    Transforms a generic alias into a concrete type which supports `issubclass`.
    If the type ends up being equivalent to a builtin, the builtin is returned.
    Includes an adaptive replacement for `type` which will iterate args as needed for subscripts.
    """

    __origin__: type
    __args__: tuple

    def __new__(cls, tp, *args):
        if tp is Any:
            return object
        if hasattr(tp, '__supertype__'):  # isinstance(..., NewType) only supported >=3.10
            tp = tp.__supertype__
        if isinstance(tp, TypeVar):
            if not tp.__constraints__:
                return object
            tp = Union[tp.__constraints__]
        origin = getattr(tp, '__origin__', tp)
        if hasattr(types, 'UnionType') and isinstance(tp, types.UnionType):
            origin = Union  # `|` syntax added in 3.10
        args = tuple(map(cls, getattr(tp, '__args__', args)))
        if set(args) <= {object} and not (origin is tuple and args):
            return origin
        bases = (origin,) if type(origin) in (type, abc.ABCMeta) else ()
        if origin is Literal:
            bases = (subtype(Union[tuple(map(type, args))]),)
        if origin is Callable.__origin__ and args[:1] == (...,):
            args = args[1:]
        namespace = {'__origin__': origin, '__args__': args}
        return type.__new__(cls, str(tp), bases, namespace)

    def __init__(self, tp, *args):
        ...

    def key(self) -> tuple:
        return self.__origin__, *self.__args__

    def __eq__(self, other) -> bool:
        return hasattr(other, '__origin__') and self.key() == subtype.key(other)

    def __hash__(self) -> int:
        return hash(self.key())

    @no_type_check
    def __subclasscheck__(self, subclass: type) -> bool:
        origin = getattr(subclass, '__origin__', subclass)
        args = getattr(subclass, '__args__', ())
        if origin is Union:
            return all(issubclass(cls, self) for cls in args)
        if self.__origin__ in (Union, type):
            return inspect.isclass(subclass) and issubclass(subclass, self.__args__)
        if self.__origin__ is Literal:
            return (origin is Literal) and set(subclass.__args__) <= set(self.__args__)
        if origin is Literal:
            return all(isinstance(arg, self) for arg in args)
        if self.__origin__ is Callable.__origin__:
            return (
                origin is Callable.__origin__
                and signature(self.__args__[-1:]) <= signature(args[-1:])  # covariant return
                and signature(args[:-1]) <= signature(self.__args__[:-1])  # contravariant args
            )
        if args == (Empty,):
            return issubclass(origin, self.__origin__)
        params = self.__args__[: -1 if self.__args__[-1:] == (...,) else None]
        return (  # check args first to avoid a recursion error in ABCMeta
            len(args) >= len(params)
            and issubclass(origin, self.__origin__)
            and all(map(issubclass, args, params))
        )

    def __instancecheck__(self, instance):
        return issubclass(self.get_type(instance), self)

    @classmethod
    def subcheck(cls, tp: type) -> bool:
        """Return whether type requires checking subscripts using `get_type`."""
        return isinstance(tp, cls) and (
            tp.__origin__ is not Union or any(map(cls.subcheck, tp.__args__))
        )

    @no_type_check
    def get_type(self, arg) -> type:
        """An adaptive version of `type`, which checks subscripts as needed.

        This is complicated by needing to potentially iterate an argument, but only if required
        because the origin type matches and has subscripts. The challenge is making the type
        checker as specific as needed, but with as minimal introspection as possible, and yet still
        performant. The strategy is to end the recursive checking at the first failure, and only
        check subsequent types which themselves are subclasses. This way `get_type` is only called
        repeatedly if it may increase the type specificity.
        """
        if not isinstance(self, subtype):  # also called as a staticmethod
            return type(arg)
        if hasattr(arg, '__orig_class__'):  # user-defined generic type
            return subtype(arg.__orig_class__)
        if self.__origin__ is type:  # a class argument is expected
            return arg
        if self.__origin__ is Literal:
            if any(arg == param and type(arg) is type(param) for param in self.__args__):
                return subtype(Literal, arg)
            return type(arg)
        if self.__origin__ is Union:  # find the most specific match
            tps = (subtype.get_type(tp_arg, arg) for tp_arg in self.__args__)
            tps = {tp for tp, tp_arg in zip(tps, self.__args__) if issubclass(tp, tp_arg)}
            if not tps:
                return type(arg)
            return functools.reduce(lambda x, y: x if issubclass(x, y) else y, tps)
        if self.__origin__ is Callable.__origin__ and isinstance(arg, Callable):
            return subtype(Callable.__origin__, *get_type_hints(arg).values())
        if not isinstance(arg, self.__origin__):  # no need to check subscripts
            return type(arg)
        if isinstance(arg, Iterator) or not isinstance(arg, Iterable):
            return type(arg)
        if issubclass(self, tuple) and self.__args__[-1:] != (...,):  # check all values
            if len(arg) != len(self.__args__):
                return type(arg)
            args = arg
        elif issubclass(self, Mapping):  # check first item
            args = next(iter(arg.items()), ())
        else:  # check first value
            args = itertools.islice(arg, 1)
        subscripts = list(map(subtype.get_type, self.__args__, args)) or [Empty]
        try:
            return subtype(type(arg), *subscripts)
        except TypeError:  # not an acceptable base type
            return subtype(self.__origin__, *subscripts)

    __call__ = get_type


def distance(cls, subclass: type) -> int:
    """Return estimated distance between classes for tie-breaking."""
    if getattr(cls, '__origin__', None) is Union:
        return min(distance(arg, subclass) for arg in cls.__args__)
    mro = type.mro(subclass)
    return mro.index(cls if cls in mro else object)


class signature(tuple):
    """A tuple of types that supports partial ordering."""

    required: int
    parents: set
    sig: inspect.Signature

    def __new__(cls, types: Iterable, required: Optional[int] = None):
        return tuple.__new__(cls, map(subtype, types))

    def __init__(self, types: Iterable, required: Optional[int] = None):
        self.required = len(self) if required is None else required

    @classmethod
    def from_hints(cls, func: Callable) -> 'signature':
        """Return evaluated type hints for positional parameters in order."""
        if not hasattr(func, '__annotations__'):
            return cls(())
        type_hints = get_type_hints(func)
        positionals = {inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD}
        params: Iterable = inspect.signature(func).parameters.values()
        params = [param for param in params if param.kind in positionals]
        # missing annotations are padded with `object`, but trailing objects are unnecessary
        indices = [index for index, param in enumerate(params) if param.name in type_hints]
        params = params[: max(indices, default=-1) + 1]
        hints = [type_hints.get(param.name, object) for param in params]
        required = sum(param.default is param.empty for param in params)
        return cls(hints, required)

    def __le__(self, other: tuple) -> bool:
        return self.required <= len(other) and all(map(issubclass, other, self))

    def __lt__(self, other: tuple) -> bool:
        return self != other and self <= other

    def __sub__(self, other: tuple) -> tuple:
        """Return relative distances, assuming self >= other."""
        return tuple(map(distance, other, self))

    def __rsub__(self, other: tuple) -> tuple:
        """Return relative distances, assuming self <= other."""
        return tuple(map(distance, self, other))

    def callable(self, *types) -> bool:
        """Check positional arity of associated function signature."""
        try:
            return not hasattr(self, 'sig') or bool(self.sig.bind_partial(*types))
        except TypeError:
            return False


REGISTERED = TypeVar("REGISTERED", bound=Callable[..., Any])


class multimethod(dict):
    """A callable directed acyclic graph of methods."""

    pending: set
    type_checkers: list

    def __new__(cls, func):
        homonym = inspect.currentframe().f_back.f_locals.get(func.__name__)
        if isinstance(homonym, multimethod):
            return homonym

        self = functools.update_wrapper(dict.__new__(cls), func)
        self.pending = set()
        self.type_checkers = []  # defaults to builtin `type`
        return self

    def __init__(self, func: Callable):
        try:
            self[signature.from_hints(func)] = func
        except (NameError, AttributeError):
            self.pending.add(func)

    @tp_overload
    def register(self, __func: REGISTERED) -> REGISTERED:
        ...  # pragma: no cover

    @tp_overload
    def register(self, *args: type) -> Callable[[REGISTERED], REGISTERED]:
        ...  # pragma: no cover

    def register(self, *args) -> Callable:
        """Decorator for registering a function.

        Optionally call with types to return a decorator for unannotated functions.
        """
        if len(args) == 1 and hasattr(args[0], '__annotations__'):
            multimethod.__init__(self, *args)
            return self if self.__name__ == args[0].__name__ else args[0]  # type: ignore
        return lambda func: self.__setitem__(args, func) or func

    def __get__(self, instance, owner):
        return self if instance is None else types.MethodType(self, instance)

    def parents(self, types: tuple) -> set:
        """Find immediate parents of potential key."""
        parents = {key for key in list(self) if isinstance(key, signature) and key < types}
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
        if not isinstance(types, signature):
            types = signature(types)
        parents = types.parents = self.parents(types)
        with contextlib.suppress(ValueError):
            types.sig = inspect.signature(func)
        self.pop(types, None)  # ensure key is overwritten
        for key in self:
            if types < key and (not parents or parents & key.parents):
                key.parents -= parents
                key.parents.add(types)
        self.type_checkers += [type] * (len(types) - len(self.type_checkers))
        for index, (cls, type_checker) in enumerate(zip(types, self.type_checkers)):
            if subtype.subcheck(cls):  # switch to slower generic type checker
                if type_checker is not type:
                    if issubclass(type_checker, cls):
                        cls = type_checker
                    else:
                        cls = subtype(Union[type_checker, cls])
                self.type_checkers[index] = cls
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
        groups = collections.defaultdict(list)
        for key in self.parents(types):
            if key.callable(*types):
                groups[types - key].append(key)
        keys = groups[min(groups)] if groups else []
        funcs = {self[key] for key in keys}
        if len(funcs) == 1:
            return self.setdefault(types, *funcs)  # type: ignore
        msg = f"{self.__name__}: {len(keys)} methods found"  # type: ignore
        raise DispatchError(msg, types, keys)

    def __call__(self, *args, **kwargs):
        """Resolve and dispatch to best method."""
        if self.pending:  # check first to avoid function call
            self.evaluate()
        func = self[tuple(func(arg) for func, arg in zip(self.type_checkers, args))]
        try:
            return func(*args, **kwargs)
        except TypeError as ex:
            raise DispatchError(f"Function {func.__code__}") from ex

    def evaluate(self):
        """Evaluate any pending forward references."""
        while self.pending:
            func = self.pending.pop()
            self[signature.from_hints(func)] = func

    @property
    def docstring(self):
        """a descriptive docstring of all registered functions"""
        docs = []
        for key, func in self.items():
            sig = getattr(key, 'sig', '')
            if func.__doc__:
                docs.append(f'{func.__name__}{sig}\n    {func.__doc__}')
        return '\n\n'.join(docs)


RETURN = TypeVar("RETURN")


class multidispatch(multimethod, Dict[Tuple[type, ...], Callable[..., RETURN]]):
    """Wrapper for compatibility with `functools.singledispatch`.

    Only uses the [register][multimethod.multimethod.register] method instead of namespace lookup.
    Allows dispatching on keyword arguments based on the first function signature.
    """

    signature: Optional[inspect.Signature]

    def __new__(cls, func: Callable[..., RETURN]) -> "multidispatch[RETURN]":
        return functools.update_wrapper(dict.__new__(cls), func)

    def __init__(self, func: Callable[..., RETURN]) -> None:
        self.pending = set()
        self.type_checkers = []
        try:
            self.signature = inspect.signature(func)
        except ValueError:
            self.signature = None
        super().__init__(func)

    def __get__(self, instance, owner) -> Callable[..., RETURN]:
        return self if instance is None else types.MethodType(self, instance)  # type: ignore

    def __call__(self, *args: Any, **kwargs: Any) -> RETURN:
        """Resolve and dispatch to best method."""
        params = self.signature.bind(*args, **kwargs).args if (kwargs and self.signature) else args
        func = self[tuple(func(arg) for func, arg in zip(self.type_checkers, params))]
        return func(*args, **kwargs)


def isa(*types: type) -> Callable:
    """Partially bound `isinstance`."""
    types = tuple(map(subtype, types))
    return lambda arg: isinstance(arg, types)


class overload(dict):
    """Ordered functions which dispatch based on their annotated predicates."""

    pending: set
    __get__ = multimethod.__get__

    def __new__(cls, func):
        namespace = inspect.currentframe().f_back.f_locals
        self = functools.update_wrapper(super().__new__(cls), func)
        self.pending = set()
        return namespace.get(func.__name__, self)

    def __init__(self, func: Callable):
        try:
            sig = self.signature(func)
        except (NameError, AttributeError):
            self.pending.add(func)
        else:
            self[sig] = func

    @classmethod
    def signature(cls, func: Callable) -> inspect.Signature:
        for name, value in get_type_hints(func).items():
            if not callable(value) or isinstance(value, type) or hasattr(value, '__origin__'):
                func.__annotations__[name] = isa(value)
        return inspect.signature(func)

    def __call__(self, *args, **kwargs):
        """Dispatch to first matching function."""
        while self.pending:
            func = self.pending.pop()
            self[self.signature(func)] = func
        for sig in reversed(self):
            try:
                arguments = sig.bind(*args, **kwargs).arguments
            except TypeError:
                continue
            if all(
                param.annotation is param.empty or param.annotation(arguments[name])
                for name, param in sig.parameters.items()
                if name in arguments
            ):
                return self[sig](*args, **kwargs)
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
