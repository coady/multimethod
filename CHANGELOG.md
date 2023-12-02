# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased
### Changed
* Python >=3.9 required
* `isinstance` and generic dispatch optimized

## [1.10](https://pypi.org/project/multimethod/1.10/) - 2023-09-21
### Changed
* Python >=3.8 required

### Added
* `Type[...]` dispatches on class arguments
* `|` syntax for union types
* `overload` supports generics and forward references
* Dispatch on optional parameters

## [1.9.1](https://pypi.org/project/multimethod/1.9.1/) - 2022-12-21
### Fixed
* Dispatch is thread-safe

## [1.9](https://pypi.org/project/multimethod/1.9/) - 2022-09-14
### Changed
* Python 3.11 supported

### Fixed
* Fixes for `Callable` and `object` annotations

## [1.8](https://pypi.org/project/multimethod/1.8/) - 2022-04-07
* `Callable` checks parameters and return type
* Support for `NewType`

## [1.7](https://pypi.org/project/multimethod/1.7/) - 2022-01-28
* `overload` allows types and converts them to an `isa` check
* Only functions with docstrings combine signatures
* Fixes for subscripted union and literal checks

## [1.6](https://pypi.org/project/multimethod/1.6/) - 2021-09-12
* Python >=3.7 required
* Improved checking for TypeErrors
* `multidispatch` has provisional support for dispatching on keyword arguments
* `multidispatch` supports static analysis of return type 
* Fix for forward references and subscripts
* Checking type subscripts is done minimally based on each parameter
* Provisionally dispatch on `Literal` type
* Provisionally empty iterables match subscript

## [1.5](https://pypi.org/project/multimethod/1.5/) - 2021-01-29
* Postponed evaluation of nested annotations
* Variable-length tuples of homogeneous type
* Ignore default and keyword-only parameters
* Resolved ambiguous `Union` types
* Fixed an issue with name collision when defining a multimethod
* Resolved dispatch errors when annotating parameters with meta-types such as `type`

## [1.4](https://pypi.org/project/multimethod/1.4/) - 2020-08-05
* Python >=3.6 required
* Expanded support for subscripted type hints

## [1.3](https://pypi.org/project/multimethod/1.3/) - 2022-02-19
* Python 3 required
* Support for subscripted ABCs

## [1.2](https://pypi.org/project/multimethod/1.2/) - 2019-12-07
* Support for typing generics
* Stricter dispatching consistent with singledispatch

## [1.1](https://pypi.org/project/multimethod/1.1/) - 2019-06-17
* Fix for Python 2 typing backport
* Metaclass for automatic multimethods

## [1.0](https://pypi.org/project/multimethod/1.0/) - 2018-12-07
* Missing annotations default to object
* Removed deprecated dispatch stacking

## [0.7](https://pypi.org/project/multimethod/0.7/) - 2017-12-07
* Forward references allowed in type hints
* Register method
* Overloads with predicate dispatch

## [0.6](https://pypi.org/project/multimethod/0.6/) - 2017-01-02
* Multimethods can be defined inside a class

## [0.5](https://pypi.org/project/multimethod/0.5/) - 2015-09-03
* Optimized dispatching
* Support for `functools.singledispatch` syntax

## [0.4](https://pypi.org/project/multimethod/0.4/) - 2013-11-10
* Dispatch on Python 3 annotations
