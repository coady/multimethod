import abc
import collections
import contextlib
import functools
import inspect
import itertools
import types
import typing
from collections.abc import Callable, Iterable, Iterator, Mapping
from typing import Any, Literal, NewType, TypeVar, Union, get_type_hints, overload


class DispatchError(TypeError): ...


def get_origin(tp):
    return tp.__origin__ if isinstance(tp, subtype) else typing.get_origin(tp)


def get_args(tp) -> tuple:
    if isinstance(tp, subtype) or typing.get_origin(tp) is Callable:
        return getattr(tp, '__args__', ())
    return typing.get_args(tp)


def get_mro(cls) -> tuple:  # `inspect.getmro` doesn't handle all cases
    return tuple(type.mro(cls)) if isinstance(cls, type) else cls.mro()


def common_bases(*bases):
    counts = collections.Counter()
    for base in bases:
        counts.update(cls for cls in get_mro(base) if issubclass(abc.ABCMeta, type(cls)))
    return tuple(cls for cls in counts if counts[cls] == len(bases))


class subtype(abc.ABCMeta):
    """A normalized generic type which checks subscripts.

    Transforms a generic alias into a concrete type which supports `issubclass` and `isinstance`.
    If the type ends up being equivalent to a builtin, the builtin is returned.
    """

    __origin__: type
    __args__: tuple

    def __new__(cls, tp, *args):
        if tp is Any:
            return object
        if isinstance(tp, NewType):
            return cls(tp.__supertype__, *args)
        if hasattr(typing, 'TypeAliasType') and isinstance(tp, typing.TypeAliasType):
            return cls(tp.__value__, *args)
        if isinstance(tp, TypeVar):
            return cls(Union[tp.__constraints__], *args) if tp.__constraints__ else object
        if isinstance(tp, typing._AnnotatedAlias):
            return cls(tp.__origin__, *args)
        origin = get_origin(tp) or tp
        args = tuple(map(cls, get_args(tp) or args))
        if set(args) <= {object} and not (origin is tuple and args):
            return origin
        bases = (origin,) if type(origin) in (type, abc.ABCMeta) else ()
        if origin is Literal:
            bases = (cls(Union[tuple(map(type, args))]),)
        if origin is Union or isinstance(tp, types.UnionType):
            origin = types.UnionType
            bases = common_bases(*args)[:1]
            if bases[0] in args:
                return bases[0]
        if origin is Callable and args[:1] == (...,):
            args = args[1:]
        namespace = {'__origin__': origin, '__args__': args}
        return type.__new__(cls, str(tp), bases, namespace)

    def __init__(self, tp, *args): ...

    def key(self) -> tuple:
        return self.__origin__, *self.__args__

    def __eq__(self, other) -> bool:
        return hasattr(other, '__origin__') and self.key() == subtype.key(other)

    def __hash__(self) -> int:
        return hash(self.key())

    def __subclasscheck__(self, subclass):
        origin = get_origin(subclass) or subclass
        args = get_args(subclass)
        if origin is Literal:
            return all(isinstance(arg, self) for arg in args)
        if origin in (Union, types.UnionType):
            return all(issubclass(cls, self) for cls in args)
        if self.__origin__ is Literal:
            return False
        if self.__origin__ is types.UnionType:
            return issubclass(subclass, self.__args__)
        if self.__origin__ is Callable:
            return (
                origin is Callable
                and signature(self.__args__[-1:]) <= signature(args[-1:])  # covariant return
                and signature(args[:-1]) <= signature(self.__args__[:-1])  # contravariant args
            )
        return (  # check args first to avoid recursion error: python/cpython#73407
            len(args) == len(self.__args__)
            and issubclass(origin, self.__origin__)
            and all(pair[0] is pair[1] or issubclass(*pair) for pair in zip(args, self.__args__))
        )

    def __instancecheck__(self, instance):
        if self.__origin__ is Literal:
            return any(type(arg) is type(instance) and arg == instance for arg in self.__args__)
        if self.__origin__ is types.UnionType:
            return isinstance(instance, self.__args__)
        if hasattr(instance, '__orig_class__'):  # user-defined generic type
            return issubclass(instance.__orig_class__, self)
        if self.__origin__ is type:  # a class argument is expected
            return inspect.isclass(instance) and issubclass(instance, self.__args__)
        if not isinstance(instance, self.__origin__) or isinstance(instance, Iterator):
            return False
        if self.__origin__ is Callable:
            return issubclass(subtype(Callable, *get_type_hints(instance).values()), self)
        if self.__origin__ is tuple and self.__args__[-1:] != (...,):
            if len(instance) != len(self.__args__):
                return False
        elif issubclass(self, Mapping):
            instance = next(iter(instance.items()), ())
        else:
            instance = itertools.islice(instance, 1)
        return all(map(isinstance, instance, self.__args__))

    @functools.singledispatch
    def origins(self) -> Iterable[type]:
        """Return origin types which would require instance checks.

        Provisional custom usage: `subtype.origins.register(<metaclass>, lambda cls: ...)
        """
        origin = get_origin(self)
        if origin is Literal:
            yield from set(map(type, self.__args__))
        elif origin is types.UnionType:
            for arg in self.__args__:
                yield from subtype.origins(arg)
        elif origin is not None:
            yield origin


class parametric(abc.ABCMeta):
    """A type which further customizes `issubclass` and `isinstance` beyond the base type.

    Args:
        base: base type
        funcs: all predicate functions are checked against the instance
        attrs: all attributes are checked for equality
    """

    def __new__(cls, base: type, *funcs: Callable, **attrs):
        return super().__new__(cls, base.__name__, (base,), {'funcs': funcs, 'attrs': attrs})

    def __init__(self, *_, **__): ...

    def __subclasscheck__(self, subclass):
        missing = object()
        attrs = getattr(subclass, 'attrs', {})
        return (
            set(subclass.__bases__).issuperset(self.__bases__)  # python/cpython#73407
            and set(getattr(subclass, 'funcs', ())).issuperset(self.funcs)
            and all(attrs.get(name, missing) == self.attrs[name] for name in self.attrs)
        )

    def __instancecheck__(self, instance):
        missing = object()
        return (
            isinstance(instance, self.__bases__)
            and all(func(instance) for func in self.funcs)
            and all(getattr(instance, name, missing) == self.attrs[name] for name in self.attrs)
        )

    def __and__(self, other):
        (base,) = set(self.__bases__ + other.__bases__)
        return type(self)(base, *set(self.funcs + other.funcs), **(self.attrs | other.attrs))


subtype.origins.register(parametric, lambda cls: cls.__bases__)


class signature(tuple):
    """A tuple of types that supports partial ordering."""

    required: int
    parents: set
    sig: inspect.Signature

    def __new__(cls, types: Iterable, required: int | None = None):
        return tuple.__new__(cls, map(subtype, types))

    def __init__(self, types: Iterable, required: int | None = None):
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

    def callable(self, *types) -> bool:
        """Check positional arity of associated function signature."""
        try:
            return not hasattr(self, 'sig') or bool(self.sig.bind_partial(*types))
        except TypeError:
            return False

    def instances(self, *args) -> bool:
        """Return whether all arguments are instances."""
        return self.required <= len(args) and all(map(isinstance, args, self))


REGISTERED = TypeVar("REGISTERED", bound=Callable[..., Any])


class multimethod(dict):
    """A callable directed acyclic graph of methods."""

    __name__: str
    pending: set
    generics: list[tuple]  # positional bases which require instance checks

    def __new__(cls, func):
        homonym = inspect.currentframe().f_back.f_locals.get(func.__name__)
        if isinstance(homonym, multimethod):
            return homonym

        self = functools.update_wrapper(dict.__new__(cls), func)
        self.pending = set()
        self.generics = []
        return self

    def __init__(self, func: Callable):
        try:
            self[signature.from_hints(func)] = func
        except (NameError, AttributeError):
            self.pending.add(func)

    @overload
    def register(self, __func: REGISTERED) -> REGISTERED: ...  # pragma: no cover

    @overload
    def register(self, *args: type) -> Callable[[REGISTERED], REGISTERED]: ...  # pragma: no cover

    def register(self, *args) -> Callable:
        """Decorator for registering a function.

        Optionally call with types to return a decorator for unannotated functions.
        """
        if len(args) == 1 and hasattr(args[0], '__annotations__'):
            multimethod.__init__(self, *args)
            return self if self.__name__ == args[0].__name__ else args[0]
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
        return dict.__new__(type(self)).__ior__(self)

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
        for index, cls in enumerate(types):
            if origins := set(subtype.origins(cls)):
                self.generics += [()] * (index + 1 - len(self.generics))
                self.generics[index] = tuple(origins.union(self.generics[index]))
        super().__setitem__(types, func)
        self.__doc__ = self.docstring

    def __delitem__(self, types: tuple):
        self.clean()
        super().__delitem__(types)
        for key in self:
            if types in key.parents:
                key.parents = self.parents(key)
        self.__doc__ = self.docstring

    def select(self, types: tuple, keys: set[signature]) -> Callable:
        keys = {key for key in keys if key.callable(*types)}
        funcs = {self[key] for key in keys}
        if len(funcs) == 1:
            return funcs.pop()
        raise DispatchError(f"{self.__name__}: {len(keys)} methods found", types, keys)

    def __missing__(self, types: tuple) -> Callable:
        """Find and cache the next applicable method of given types."""
        self.evaluate()
        types = tuple(map(subtype, types))
        if types in self:
            return self[types]
        return self.setdefault(types, self.select(types, self.parents(types)))

    def dispatch(self, *args) -> Callable:
        self.evaluate()
        types = tuple(map(type, args))
        if not any(map(issubclass, types, self.generics)):
            return self[types]
        matches = {key for key in list(self) if isinstance(key, signature) and key.instances(*args)}
        matches -= {ancestor for match in matches for ancestor in match.parents}
        return self.select(types, matches)

    def __call__(self, *args, **kwargs):
        """Resolve and dispatch to best method."""
        func = self.dispatch(*args)
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


del overload  # raise error on legacy import
RETURN = TypeVar("RETURN")


class multidispatch(multimethod, dict[tuple[type, ...], Callable[..., RETURN]]):
    """Wrapper for compatibility with `functools.singledispatch`.

    Only uses the [register][multimethod.multimethod.register] method instead of namespace lookup.
    Allows dispatching on keyword arguments based on the first function signature.
    """

    signatures: dict[tuple, inspect.Signature]

    def __new__(cls, func: Callable[..., RETURN]) -> "multidispatch[RETURN]":
        return functools.update_wrapper(dict.__new__(cls), func)  # type: ignore

    def __init__(self, func: Callable[..., RETURN]) -> None:
        self.pending = set()
        self.generics = []
        self.signatures = {}
        self[()] = func

    def __get__(self, instance, owner) -> Callable[..., RETURN]:
        return self if instance is None else types.MethodType(self, instance)  # type: ignore

    def __setitem__(self, types: tuple, func: Callable):
        super().__setitem__(types, func)
        with contextlib.suppress(ValueError):
            signature = inspect.signature(func)
            self.signatures.setdefault(tuple(signature.parameters), signature)

    def __call__(self, *args: Any, **kwargs: Any) -> RETURN:
        """Resolve and dispatch to best method."""
        params = args
        if kwargs:
            for signature in self.signatures.values():  # pragma: no branch
                with contextlib.suppress(TypeError):
                    params = signature.bind(*args, **kwargs).args
                    break
        func = self.dispatch(*params)
        return func(*args, **kwargs)


class multimeta(type):
    """Convert all callables in namespace to multimethods."""

    class __prepare__(dict):
        def __init__(*args): ...

        def __setitem__(self, key, value):
            if callable(value):
                value = getattr(self.get(key), 'register', multimethod)(value)
            super().__setitem__(key, value)
