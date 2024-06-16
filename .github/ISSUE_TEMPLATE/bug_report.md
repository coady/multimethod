---
name: Bug report
about: Create a report to help us improve
title: ''
labels: ''
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is. Please open separate issues if there are multiple topics.

**To Reproduce**
Please isolate the issue to the smallest reproducible example, with no dependencies. Most dispatch errors are caused by an unsupported type - one that does not implement `issubclass` correctly.

**Expected behavior**
For relevant types, what is the output and expectation of:
```python
issubclass(..., MyType)
issubclass(MyType, ...)
```

If those error, `subtype` can be used to check if `multitmethod` has custom support. What is the the output and expectation of:
```python
from multimethod import subtype

issubclass(..., subtype(MyType))
issubclass(subtype(MyType), ...)
```
