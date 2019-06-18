import sys

py2 = sys.version_info < (3,)


def pytest_ignore_collect(path, config):
    return py2 and path.basename == 'test_py3.py'
