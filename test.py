import unittest
import collections
from multimethod import multimethod, DispatchError

# roshambo
class rock(object):
    pass

class paper(object):
    pass

class scissors(object):
    pass

@multimethod(scissors, rock)
@multimethod(rock, scissors)
def roshambo(left, right):
    return 'rock smashes scissors'

@multimethod(paper, scissors)
@multimethod(scissors, paper)
def roshambo(left, right):
    return 'scissors cut paper'

@multimethod(rock, paper)
@multimethod(paper, rock)
def roshambo(left, right):
    return 'paper covers rock'

@multimethod(object, object)
def roshambo(left, right):
    return 'tie'

# string join
class tree(list):
    def walk(self):
        for value in self:
            if isinstance(value, type(self)):
                for subvalue in value.walk():
                    yield subvalue
            else:
                yield value

class bracket(tuple):
    def __new__(cls, left, right):
        return tuple.__new__(cls, (left, right))

@multimethod(collections.Iterable, str)
def join(seq, sep):
    return sep.join(map(str, seq))

@multimethod(object, bracket)
def join(seq, sep):
    return sep[0] + join(seq, sep[1]+sep[0]) + sep[1]

@multimethod(tree, object)
def join(seq, sep):
    return join(seq.walk(), sep)

class TestCase(unittest.TestCase):

    def testRoshambo(self):
        r, p, s = rock(), paper(), scissors()
        assert len(roshambo) == 7 and not roshambo.cache
        assert roshambo(r, p) == 'paper covers rock'
        assert roshambo(p, r) == 'paper covers rock'
        assert roshambo(r, s) == 'rock smashes scissors'
        assert roshambo(p, s) == 'scissors cut paper'
        assert roshambo(r, r) == 'tie'
        assert roshambo.cache
        del roshambo[object, object]
        del roshambo[rock, paper]
        assert len(roshambo) == 5 and not roshambo.cache
        self.assertRaises(TypeError, roshambo, r, r)

    def testJoin(self):
        sep = '<>'
        seq = [0, tree([1]), 2]
        assert list(tree(seq).walk()) == list(range(3))
        assert join(seq, sep) == '0<>[1]<>2'
        assert join(tree(seq), sep) == '0<>1<>2'
        assert join(seq, bracket(*sep)) == '<0><[1]><2>'
        assert join(tree(seq), bracket(*sep)) == '<0><1><2>'

    def testStrict(self):
        func = multimethod.new(strict=True)
        @multimethod(int, object)
        @multimethod(object, int)
        def func(x, y):
            pass
        assert func(0, None) is func(None, 0) is None
        self.assertRaises(DispatchError, func, 0, 0)

    def testAnnotations(self):
        self.assertRaises(DispatchError, annotated, 0, 0)
        assert annotated(1, 2.0) == 2

try:
    exec('@multimethod\ndef annotated(x:int, y:float, z=None): return x * y')
except SyntaxError:
    del TestCase.testAnnotations

if __name__ == '__main__':
    unittest.main()
