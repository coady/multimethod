import unittest
from multimethod import multimethod

# roshambo
class rock(object):
    pass

class paper(object):
    pass

class scissors(object):
    pass

@multimethod(object, object)
def roshambo(left, right):
    return 'tie'

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

@multimethod(object, str)
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
        assert roshambo(r, p) == 'paper covers rock'
        assert roshambo(p, r) == 'paper covers rock'
        assert roshambo(r, s) == 'rock smashes scissors'
        assert roshambo(p, s) == 'scissors cut paper'
        assert len(roshambo) == 7 and not roshambo.cache
        assert roshambo(r, r) == 'tie'
        assert roshambo.cache
        del roshambo[object, object]
        assert not roshambo.cache
        self.assertRaises(TypeError, roshambo, r, r)
    def testJoin(self):
        sep = '<>'
        seq = [0, tree([1]), 2]
        assert list(tree(seq).walk()) == range(3)
        assert join(seq, sep) == '0<>[1]<>2'
        assert join(tree(seq), sep) == '0<>1<>2'
        assert join(seq, bracket(*sep)) == '<0><[1]><2>'
        assert join(tree(seq), bracket(*sep)) == '<0><1><2>'

if __name__ == '__main__':
    unittest.main()
