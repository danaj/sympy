from collections import defaultdict
import random
from operator import gt

from sympy.core.decorators import deprecated
from sympy.core import Basic, C

# this is the logical location of these functions
from sympy.core.compatibility import (
    as_int, combinations, combinations_with_replacement,
    default_sort_key, is_sequence, iterable, permutations,
    product as cartes, ordered, next, bin
)


def flatten(iterable, levels=None, cls=None):
    """
    Recursively denest iterable containers.

    >>> from sympy.utilities.iterables import flatten

    >>> flatten([1, 2, 3])
    [1, 2, 3]
    >>> flatten([1, 2, [3]])
    [1, 2, 3]
    >>> flatten([1, [2, 3], [4, 5]])
    [1, 2, 3, 4, 5]
    >>> flatten([1.0, 2, (1, None)])
    [1.0, 2, 1, None]

    If you want to denest only a specified number of levels of
    nested containers, then set ``levels`` flag to the desired
    number of levels::

    >>> ls = [[(-2, -1), (1, 2)], [(0, 0)]]

    >>> flatten(ls, levels=1)
    [(-2, -1), (1, 2), (0, 0)]

    If cls argument is specified, it will only flatten instances of that
    class, for example:

    >>> from sympy.core import Basic
    >>> class MyOp(Basic):
    ...     pass
    ...
    >>> flatten([MyOp(1, MyOp(2, 3))], cls=MyOp)
    [1, 2, 3]

    adapted from http://kogs-www.informatik.uni-hamburg.de/~meine/python_tricks
    """
    if levels is not None:
        if not levels:
            return iterable
        elif levels > 0:
            levels -= 1
        else:
            raise ValueError(
                "expected non-negative number of levels, got %s" % levels)

    if cls is None:
        reducible = lambda x: is_sequence(x, set)
    else:
        reducible = lambda x: isinstance(x, cls)

    result = []

    for el in iterable:
        if reducible(el):
            if hasattr(el, 'args'):
                el = el.args
            result.extend(flatten(el, levels=levels, cls=cls))
        else:
            result.append(el)

    return result


def unflatten(iter, n=2):
    """Group ``iter`` into tuples of length ``n``. Raise an error if
    the length of ``iter`` is not a multiple of ``n``.
    """
    if n < 1 or len(iter) % n:
        raise ValueError('iter length is not a multiple of %i' % n)
    return zip(*(iter[i::n] for i in xrange(n)))


def reshape(seq, how):
    """Reshape the sequence according to the template in ``how``.

    Examples
    ========

    >>> from sympy.utilities import reshape
    >>> seq = range(1, 9)

    >>> reshape(seq, [4]) # lists of 4
    [[1, 2, 3, 4], [5, 6, 7, 8]]

    >>> reshape(seq, (4,)) # tuples of 4
    [(1, 2, 3, 4), (5, 6, 7, 8)]

    >>> reshape(seq, (2, 2)) # tuples of 4
    [(1, 2, 3, 4), (5, 6, 7, 8)]

    >>> reshape(seq, (2, [2])) # (i, i, [i, i])
    [(1, 2, [3, 4]), (5, 6, [7, 8])]

    >>> reshape(seq, ((2,), [2])) # etc....
    [((1, 2), [3, 4]), ((5, 6), [7, 8])]

    >>> reshape(seq, (1, [2], 1))
    [(1, [2, 3], 4), (5, [6, 7], 8)]

    >>> reshape(tuple(seq), ([[1], 1, (2,)],))
    (([[1], 2, (3, 4)],), ([[5], 6, (7, 8)],))

    >>> reshape(tuple(seq), ([1], 1, (2,)))
    (([1], 2, (3, 4)), ([5], 6, (7, 8)))

    >>> reshape(range(12), [2, [3], set([2]), (1, (3,), 1)])
    [[0, 1, [2, 3, 4], set([5, 6]), (7, (8, 9, 10), 11)]]

    """
    m = sum(flatten(how))
    n, rem = divmod(len(seq), m)
    if m < 0 or rem:
        raise ValueError('template must sum to positive number '
        'that divides the length of the sequence')
    i = 0
    container = type(how)
    rv = [None]*n
    for k in range(len(rv)):
        rv[k] = []
        for hi in how:
            if type(hi) is int:
                rv[k].extend(seq[i: i + hi])
                i += hi
            else:
                n = sum(flatten(hi))
                hi_type = type(hi)
                rv[k].append(hi_type(reshape(seq[i: i + n], hi)[0]))
                i += n
        rv[k] = container(rv[k])
    return type(seq)(rv)


def group(seq, multiple=True):
    """
    Splits a sequence into a list of lists of equal, adjacent elements.

    Examples
    ========

    >>> from sympy.utilities.iterables import group

    >>> group([1, 1, 1, 2, 2, 3])
    [[1, 1, 1], [2, 2], [3]]
    >>> group([1, 1, 1, 2, 2, 3], multiple=False)
    [(1, 3), (2, 2), (3, 1)]
    >>> group([1, 1, 3, 2, 2, 1], multiple=False)
    [(1, 2), (3, 1), (2, 2), (1, 1)]

    See Also
    ========
    multiset
    """
    if not seq:
        return []

    current, groups = [seq[0]], []

    for elem in seq[1:]:
        if elem == current[-1]:
            current.append(elem)
        else:
            groups.append(current)
            current = [elem]

    groups.append(current)

    if multiple:
        return groups

    for i, current in enumerate(groups):
        groups[i] = (current[0], len(current))

    return groups


def multiset(seq):
    """Return the hashable sequence in multiset form with values being the
    multiplicity of the item in the sequence.

    Examples
    ========

    >>> from sympy.utilities.iterables import multiset
    >>> multiset('mississippi')
    {'i': 4, 'm': 1, 'p': 2, 's': 4}

    See Also
    ========
    group
    """
    rv = defaultdict(int)
    for s in seq:
        rv[s] += 1
    return dict(rv)


def postorder_traversal(node, keys=None):
    """
    Do a postorder traversal of a tree.

    This generator recursively yields nodes that it has visited in a postorder
    fashion. That is, it descends through the tree depth-first to yield all of
    a node's children's postorder traversal before yielding the node itself.

    Parameters
    ==========

    node : sympy expression
        The expression to traverse.
    keys : (default None) sort key(s)
        The key(s) used to sort args of Basic objects. When None, args of Basic
        objects are processed in arbitrary order. If key is defined, it will
        be passed along to ordered() as the only key(s) to use to sort the
        arguments; if ``key`` is simply True then the default keys of
        ``ordered`` will be used (node count and default_sort_key).

    Yields
    ======
    subtree : sympy expression
        All of the subtrees in the tree.

    Examples
    ========

    >>> from sympy.utilities.iterables import postorder_traversal
    >>> from sympy.abc import w, x, y, z

    The nodes are returned in the order that they are encountered unless key
    is given; simply passing key=True will guarantee that the traversal is
    unique.

    >>> list(postorder_traversal(w + (x + y)*z)) # doctest: +SKIP
    [z, y, x, x + y, z*(x + y), w, w + z*(x + y)]
    >>> list(postorder_traversal(w + (x + y)*z, keys=True))
    [w, z, x, y, x + y, z*(x + y), w + z*(x + y)]


    """
    if isinstance(node, Basic):
        args = node.args
        if keys:
            if keys != True:
                args = ordered(args, keys, default=False)
            else:
                args = ordered(args)
        for arg in args:
            for subtree in postorder_traversal(arg, keys):
                yield subtree
    elif iterable(node):
        for item in node:
            for subtree in postorder_traversal(item, keys):
                yield subtree
    yield node


def interactive_traversal(expr):
    """Traverse a tree asking a user which branch to choose. """
    from sympy.printing import pprint

    RED, BRED = '\033[0;31m', '\033[1;31m'
    GREEN, BGREEN = '\033[0;32m', '\033[1;32m'
    YELLOW, BYELLOW = '\033[0;33m', '\033[1;33m'
    BLUE, BBLUE = '\033[0;34m', '\033[1;34m'
    MAGENTA, BMAGENTA = '\033[0;35m', '\033[1;35m'
    CYAN, BCYAN = '\033[0;36m', '\033[1;36m'
    END = '\033[0m'

    def cprint(*args):
        print "".join(map(str, args)) + END

    def _interactive_traversal(expr, stage):
        if stage > 0:
            print

        cprint("Current expression (stage ", BYELLOW, stage, END, "):")
        print BCYAN
        pprint(expr)
        print END

        if isinstance(expr, Basic):
            if expr.is_Add:
                args = expr.as_ordered_terms()
            elif expr.is_Mul:
                args = expr.as_ordered_factors()
            else:
                args = expr.args
        elif hasattr(expr, "__iter__"):
            args = list(expr)
        else:
            return expr

        n_args = len(args)

        if not n_args:
            return expr

        for i, arg in enumerate(args):
            cprint(GREEN, "[", BGREEN, i, GREEN, "] ", BLUE, type(arg), END)
            pprint(arg)
            print

        if n_args == 1:
            choices = '0'
        else:
            choices = '0-%d' % (n_args - 1)

        try:
            choice = raw_input("Your choice [%s,f,l,r,d,?]: " % choices)
        except EOFError:
            result = expr
            print
        else:
            if choice == '?':
                cprint(RED, "%s - select subexpression with the given index" %
                       choices)
                cprint(RED, "f - select the first subexpression")
                cprint(RED, "l - select the last subexpression")
                cprint(RED, "r - select a random subexpression")
                cprint(RED, "d - done\n")

                result = _interactive_traversal(expr, stage)
            elif choice in ['d', '']:
                result = expr
            elif choice == 'f':
                result = _interactive_traversal(args[0], stage + 1)
            elif choice == 'l':
                result = _interactive_traversal(args[-1], stage + 1)
            elif choice == 'r':
                result = _interactive_traversal(random.choice(args), stage + 1)
            else:
                try:
                    choice = int(choice)
                except ValueError:
                    cprint(BRED,
                           "Choice must be a number in %s range\n" % choices)
                    result = _interactive_traversal(expr, stage)
                else:
                    if choice < 0 or choice >= n_args:
                        cprint(BRED, "Choice must be in %s range\n" % choices)
                        result = _interactive_traversal(expr, stage)
                    else:
                        result = _interactive_traversal(args[choice], stage + 1)

        return result

    return _interactive_traversal(expr, 0)


def ibin(n, bits=0, str=False):
    """Return a list of length ``bits`` corresponding to the binary value
    of ``n`` with small bits to the right (last). If bits is omitted, the
    length will be the number required to represent ``n``. If the bits are
    desired in reversed order, use the [::-1] slice of the returned list.

    If a sequence of all bits-length lists starting from [0, 0,..., 0]
    through [1, 1, ..., 1] are desired, pass a non-integer for bits, e.g.
    'all'.

    If the bit *string* is desired pass ``str=True``.

    Examples
    ========

    >>> from sympy.utilities.iterables import ibin
    >>> ibin(2)
    [1, 0]
    >>> ibin(2, 4)
    [0, 0, 1, 0]
    >>> ibin(2, 4)[::-1]
    [0, 1, 0, 0]

    If all lists corresponding to 0 to 2**n - 1, pass a non-integer
    for bits:

    >>> bits = 2
    >>> for i in ibin(2, 'all'):
    ...     print i
    (0, 0)
    (0, 1)
    (1, 0)
    (1, 1)

    If a bit string is desired of a given length, use str=True:

    >>> n = 123
    >>> bits = 10
    >>> ibin(n, bits, str=True)
    '0001111011'
    >>> ibin(n, bits, str=True)[::-1]  # small bits left
    '1101111000'
    >>> list(ibin(3, 'all', str=True))
    ['000', '001', '010', '011', '100', '101', '110', '111']

    """
    if not str:
        try:
            bits = as_int(bits)
            return [1 if i == "1" else 0 for i in bin(n)[2:].rjust(bits, "0")]
        except ValueError:
            return variations(range(2), n, repetition=True)
    else:
        try:
            bits = as_int(bits)
            return bin(n)[2:].rjust(bits, "0")
        except ValueError:
            return (bin(i)[2:].rjust(n, "0") for i in range(2**n))


def variations(seq, n, repetition=False):
    """Returns a generator of the n-sized variations of ``seq`` (size N).
    ``repetition`` controls whether items in ``seq`` can appear more than once;

    Examples
    ========

    variations(seq, n) will return N! / (N - n)! permutations without
    repetition of seq's elements:

        >>> from sympy.utilities.iterables import variations
        >>> list(variations([1, 2], 2))
        [(1, 2), (2, 1)]

    variations(seq, n, True) will return the N**n permutations obtained
    by allowing repetition of elements:

        >>> list(variations([1, 2], 2, repetition=True))
        [(1, 1), (1, 2), (2, 1), (2, 2)]

    If you ask for more items than are in the set you get the empty set unless
    you allow repetitions:

        >>> list(variations([0, 1], 3, repetition=False))
        []
        >>> list(variations([0, 1], 3, repetition=True))[:4]
        [(0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 1, 1)]

    See Also
    ========

    sympy.core.compatibility.permutations
    sympy.core.compatibility.product
    """
    from sympy.core.compatibility import product

    if not repetition:
        seq = tuple(seq)
        if len(seq) < n:
            return
        for i in permutations(seq, n):
            yield i
    else:
        if n == 0:
            yield ()
        else:
            for i in product(seq, repeat=n):
                yield i


def subsets(seq, k=None, repetition=False):
    """Generates all k-subsets (combinations) from an n-element set, seq.

       A k-subset of an n-element set is any subset of length exactly k. The
       number of k-subsets of an n-element set is given by binomial(n, k),
       whereas there are 2**n subsets all together. If k is None then all
       2**n subsets will be returned from shortest to longest.

       Examples
       ========

       >>> from sympy.utilities.iterables import subsets

       subsets(seq, k) will return the n!/k!/(n - k)! k-subsets (combinations)
       without repetition, i.e. once an item has been removed, it can no
       longer be "taken":

           >>> list(subsets([1, 2], 2))
           [(1, 2)]
           >>> list(subsets([1, 2]))
           [(), (1,), (2,), (1, 2)]
           >>> list(subsets([1, 2, 3], 2))
           [(1, 2), (1, 3), (2, 3)]


       subsets(seq, k, repetition=True) will return the (n - 1 + k)!/k!/(n - 1)!
       combinations *with* repetition:

           >>> list(subsets([1, 2], 2, repetition=True))
           [(1, 1), (1, 2), (2, 2)]

       If you ask for more items than are in the set you get the empty set unless
       you allow repetitions:

           >>> list(subsets([0, 1], 3, repetition=False))
           []
           >>> list(subsets([0, 1], 3, repetition=True))
           [(0, 0, 0), (0, 0, 1), (0, 1, 1), (1, 1, 1)]

       """
    if k is None:
        for k in range(len(seq) + 1):
            for i in subsets(seq, k, repetition):
                yield i
    else:
        if not repetition:
            for i in combinations(seq, k):
                yield i
        else:
            for i in combinations_with_replacement(seq, k):
                yield i


def numbered_symbols(prefix='x', cls=None, start=0, *args, **assumptions):
    """
    Generate an infinite stream of Symbols consisting of a prefix and
    increasing subscripts.

    Parameters
    ==========

    prefix : str, optional
        The prefix to use. By default, this function will generate symbols of
        the form "x0", "x1", etc.

    cls : class, optional
        The class to use. By default, it uses Symbol, but you can also use Wild or Dummy.

    start : int, optional
        The start number.  By default, it is 0.

    Returns
    =======

    sym : Symbol
        The subscripted symbols.
    """

    if cls is None:
        # We can't just make the default cls=C.Symbol because it isn't
        # imported yet.
        cls = C.Symbol

    while True:
        name = '%s%s' % (prefix, start)
        yield cls(name, *args, **assumptions)
        start += 1


def capture(func):
    """Return the printed output of func().

    `func` should be a function without arguments that produces output with
    print statements.

    >>> from sympy.utilities.iterables import capture
    >>> from sympy import pprint
    >>> from sympy.abc import x
    >>> def foo():
    ...     print 'hello world!'
    ...
    >>> 'hello' in capture(foo) # foo, not foo()
    True
    >>> capture(lambda: pprint(2/x))
    '2\\n-\\nx\\n'

    """
    import StringIO
    import sys

    stdout = sys.stdout
    sys.stdout = file = StringIO.StringIO()
    try:
        func()
    finally:
        sys.stdout = stdout
    return file.getvalue()


def sift(seq, keyfunc):
    """
    Sift the sequence, ``seq`` into a dictionary according to keyfunc.

    OUTPUT: each element in expr is stored in a list keyed to the value
    of keyfunc for the element.

    Examples
    ========

    >>> from sympy.utilities import sift
    >>> from sympy.abc import x, y
    >>> from sympy import sqrt, exp

    >>> sift(range(5), lambda x: x % 2)
    {0: [0, 2, 4], 1: [1, 3]}

    sift() returns a defaultdict() object, so any key that has no matches will
    give [].

    >>> sift([x], lambda x: x.is_commutative)
    {True: [x]}
    >>> _[False]
    []

    Sometimes you won't know how many keys you will get:

    >>> sift([sqrt(x), exp(x), (y**x)**2],
    ...      lambda x: x.as_base_exp()[0])
    {E: [exp(x)], x: [sqrt(x)], y: [y**(2*x)]}

    If you need to sort the sifted items it might be better to use
    ``ordered`` which can economically apply multiple sort keys
    to a squence while sorting.

    See Also
    ========
    ordered
    """
    m = defaultdict(list)
    for i in seq:
        m[keyfunc(i)].append(i)
    return m


def take(iter, n):
    """Return ``n`` items from ``iter`` iterator. """
    return [ value for _, value in zip(xrange(n), iter) ]


def dict_merge(*dicts):
    """Merge dictionaries into a single dictionary. """
    merged = {}

    for dict in dicts:
        merged.update(dict)

    return merged


def common_prefix(*seqs):
    """Return the subsequence that is a common start of sequences in ``seqs``.

    >>> from sympy.utilities.iterables import common_prefix
    >>> common_prefix(range(3))
    [0, 1, 2]
    >>> common_prefix(range(3), range(4))
    [0, 1, 2]
    >>> common_prefix([1, 2, 3], [1, 2, 5])
    [1, 2]
    >>> common_prefix([1, 2, 3], [1, 3, 5])
    [1]
    """
    if any(not s for s in seqs):
        return []
    elif len(seqs) == 1:
        return seqs[0]
    i = 0
    for i in range(min(len(s) for s in seqs)):
        if not all(seqs[j][i] == seqs[0][i] for j in xrange(len(seqs))):
            break
    else:
        i += 1
    return seqs[0][:i]


def common_suffix(*seqs):
    """Return the subsequence that is a common ending of sequences in ``seqs``.

    >>> from sympy.utilities.iterables import common_suffix
    >>> common_suffix(range(3))
    [0, 1, 2]
    >>> common_suffix(range(3), range(4))
    []
    >>> common_suffix([1, 2, 3], [9, 2, 3])
    [2, 3]
    >>> common_suffix([1, 2, 3], [9, 7, 3])
    [3]
    """

    if any(not s for s in seqs):
        return []
    elif len(seqs) == 1:
        return seqs[0]
    i = 0
    for i in range(-1, -min(len(s) for s in seqs) - 1, -1):
        if not all(seqs[j][i] == seqs[0][i] for j in xrange(len(seqs))):
            break
    else:
        i -= 1
    if i == -1:
        return []
    else:
        return seqs[0][i + 1:]


def prefixes(seq):
    """
    Generate all prefixes of a sequence.

    Examples
    ========

    >>> from sympy.utilities.iterables import prefixes

    >>> list(prefixes([1,2,3,4]))
    [[1], [1, 2], [1, 2, 3], [1, 2, 3, 4]]

    """
    n = len(seq)

    for i in xrange(n):
        yield seq[:i + 1]


def postfixes(seq):
    """
    Generate all postfixes of a sequence.

    Examples
    ========

    >>> from sympy.utilities.iterables import postfixes

    >>> list(postfixes([1,2,3,4]))
    [[4], [3, 4], [2, 3, 4], [1, 2, 3, 4]]

    """
    n = len(seq)

    for i in xrange(n):
        yield seq[n - i - 1:]


def topological_sort(graph, key=None):
    r"""
    Topological sort of graph's vertices.

    Parameters
    ==========

    ``graph`` : ``tuple[list, list[tuple[T, T]]``
        A tuple consisting of a list of vertices and a list of edges of
        a graph to be sorted topologically.

    ``key`` : ``callable[T]`` (optional)
        Ordering key for vertices on the same level. By default the natural
        (e.g. lexicographic) ordering is used (in this case the base type
        must implement ordering relations).

    Examples
    ========

    Consider a graph::

        +---+     +---+     +---+
        | 7 |\    | 5 |     | 3 |
        +---+ \   +---+     +---+
          |   _\___/ ____   _/ |
          |  /  \___/    \ /   |
          V  V           V V   |
         +----+         +---+  |
         | 11 |         | 8 |  |
         +----+         +---+  |
          | | \____   ___/ _   |
          | \      \ /    / \  |
          V  \     V V   /  V  V
        +---+ \   +---+ |  +----+
        | 2 |  |  | 9 | |  | 10 |
        +---+  |  +---+ |  +----+
               \________/

    where vertices are integers. This graph can be encoded using
    elementary Python's data structures as follows::

        >>> V = [2, 3, 5, 7, 8, 9, 10, 11]
        >>> E = [(7, 11), (7, 8), (5, 11), (3, 8), (3, 10),
        ...      (11, 2), (11, 9), (11, 10), (8, 9)]

    To compute a topological sort for graph ``(V, E)`` issue::

        >>> from sympy.utilities.iterables import topological_sort

        >>> topological_sort((V, E))
        [3, 5, 7, 8, 11, 2, 9, 10]

    If specific tie breaking approach is needed, use ``key`` parameter::

        >>> topological_sort((V, E), key=lambda v: -v)
        [7, 5, 11, 3, 10, 8, 9, 2]

    Only acyclic graphs can be sorted. If the input graph has a cycle,
    then :py:exc:`ValueError` will be raised::

        >>> topological_sort((V, E + [(10, 7)]))
        Traceback (most recent call last):
        ...
        ValueError: cycle detected

    .. seealso:: http://en.wikipedia.org/wiki/Topological_sorting

    """
    V, E = graph

    L = []
    S = set(V)
    E = list(E)

    for v, u in E:
        S.discard(u)

    if key is None:
        key = lambda value: value

    S = sorted(S, key=key, reverse=True)

    while S:
        node = S.pop()
        L.append(node)

        for u, v in list(E):
            if u == node:
                E.remove((u, v))

                for _u, _v in E:
                    if v == _v:
                        break
                else:
                    kv = key(v)

                    for i, s in enumerate(S):
                        ks = key(s)

                        if kv > ks:
                            S.insert(i, v)
                            break
                    else:
                        S.append(v)

    if E:
        raise ValueError("cycle detected")
    else:
        return L


def rotate_left(x, y):
    """
    Left rotates a list x by the number of steps specified
    in y.

    Examples
    ========

    >>> from sympy.utilities.iterables import rotate_left
    >>> a = [0, 1, 2]
    >>> rotate_left(a, 1)
    [1, 2, 0]
    """
    if len(x) == 0:
        return []
    y = y % len(x)
    return x[y:] + x[:y]


def rotate_right(x, y):
    """
    Left rotates a list x by the number of steps specified
    in y.

    Examples
    ========

    >>> from sympy.utilities.iterables import rotate_right
    >>> a = [0, 1, 2]
    >>> rotate_right(a, 1)
    [2, 0, 1]
    """
    if len(x) == 0:
        return []
    y = len(x) - y % len(x)
    return x[y:] + x[:y]


def multiset_combinations(m, n, g=None):
    """
    Return the unique combinations of size ``n`` from multiset ``m``.

    Examples
    ========

    >>> from sympy.utilities.iterables import multiset_combinations
    >>> from sympy.core.compatibility import combinations
    >>> [''.join(i) for i in  multiset_combinations('baby', 3)]
    ['abb', 'aby', 'bby']

    >>> def count(f, s): return len(list(f(s, 3)))

    The number of combinations depends on the number of letters; the
    number of unique combinations depends on how the letters are
    repeated.

    >>> s1 = 'abracadabra'
    >>> s2 = 'banana tree'
    >>> count(combinations, s1), count(multiset_combinations, s1)
    (165, 23)
    >>> count(combinations, s2), count(multiset_combinations, s2)
    (165, 54)

    """
    if g is None:
        if type(m) is dict:
            if n > sum(m.values()):
                return
            g = [[k, m[k]] for k in ordered(m)]
        else:
            m = list(m)
            if n > len(m):
                return
            try:
                m = multiset(m)
                g = [(k, m[k]) for k in ordered(m)]
            except TypeError:
                m = list(ordered(m))
                g = [list(i) for i in group(m, multiple=False)]
        del m
    if sum(v for k, v in g) < n or not n:
        yield []
    else:
        for i, (k, v) in enumerate(g):
            if v >= n:
                yield [k]*n
                v = n - 1
            for v in range(min(n, v), 0, -1):
                for j in multiset_combinations(None, n - v, g[i + 1:]):
                    rv = [k]*v + j
                    if len(rv) == n:
                        yield rv


def multiset_permutations(m, size=None, g=None):
    """
    Return the unique permutations of multiset ``m``.

    Examples
    ========

    >>> from sympy.utilities.iterables import multiset_permutations
    >>> from sympy import factorial
    >>> [''.join(i) for i in multiset_permutations('aab')]
    ['aab', 'aba', 'baa']
    >>> factorial(len('banana'))
    720
    >>> len(list(multiset_permutations('banana')))
    60
    """
    if g is None:
        if type(m) is dict:
            g = [[k, m[k]] for k in ordered(m)]
        else:
            m = list(ordered(m))
            g = [list(i) for i in group(m, multiple=False)]
        del m
    do = [gi for gi in g if gi[1] > 0]
    SUM = sum([gi[1] for gi in do])
    if not do or size is not None and (size > SUM or size < 1):
        if size < 1:
            yield []
        return
    elif size == 1:
        for k, v in do:
            yield [k]
    elif len(do) == 1:
        k, v = do[0]
        v = v if size is None else (size if size <= v else 0)
        yield [k for i in range(v)]
    elif all(v == 1 for k, v in do):
        for p in permutations([k for k, v in do], size):
            yield list(p)
    else:
        size = size if size is not None else SUM
        for i, (k, v) in enumerate(do):
            do[i][1] -= 1
            for j in multiset_permutations(None, size - 1, do):
                if j:
                    yield [k] + j
            do[i][1] += 1


def _partition(seq, vector, m=None):
    """
    Return the partion of seq as specified by the partition vector.

    Examples
    ========

    >>> from sympy.utilities.iterables import _partition
    >>> _partition('abcde', [1, 0, 1, 2, 0])
    [['b', 'e'], ['a', 'c'], ['d']]

    Specifying the number of bins in the partition is optional:

    >>> _partition('abcde', [1, 0, 1, 2, 0], 3)
    [['b', 'e'], ['a', 'c'], ['d']]

    The output of _set_partitions can be passed as follows:

    >>> output = (3, [1, 0, 1, 2, 0])
    >>> _partition('abcde', *output)
    [['b', 'e'], ['a', 'c'], ['d']]

    See Also
    ========
    combinatorics.partitions.Partition.from_rgs()

    """
    if m is None:
        m = max(vector) + 1
    elif type(vector) is int:  # entered as m, vector
        vector, m = m, vector
    p = [[] for i in range(m)]
    for i, v in enumerate(vector):
        p[v].append(seq[i])
    return p


def _set_partitions(n):
    """Cycle through all partions of n elements, yielding the
    current number of partitions, ``m``, and a mutable list, ``q``
    such that element[i] is in part q[i] of the partition.

    NOTE: ``q`` is modified in place and generally should not be changed
    between function calls.

    Examples
    ========

    >>> from sympy.utilities.iterables import _set_partitions, _partition
    >>> for m, q in _set_partitions(3):
    ...     print m, q, _partition('abc', q, m)
    1 [0, 0, 0] [['a', 'b', 'c']]
    2 [0, 0, 1] [['a', 'b'], ['c']]
    2 [0, 1, 0] [['a', 'c'], ['b']]
    2 [0, 1, 1] [['a'], ['b', 'c']]
    3 [0, 1, 2] [['a'], ['b'], ['c']]

    Notes
    =====

    This algorithm is similar to, and solves the same problem as,
    Algorithm 7.2.1.5H, from volume 4A of Knuth's The Art of Computer
    Programming.  Knuth uses the term "restricted growth string" where
    this code refers to a "partition vector". In each case, the meaning is
    the same: the value in the ith element of the vector specifies to
    which part the ith set element is to be assigned.

    At the lowest level, this code implements an n-digit big-endian
    counter (stored in the array q) which is incremented (with carries) to
    get the next partition in the sequence.  A special twist is that a
    digit is constrained to be at most one greater than the maximum of all
    the digits to the left of it.  The array p maintains this maximum, so
    that the code can efficiently decide when a digit can be incremented
    in place or whether it needs to be reset to 0 and trigger a carry to
    the next digit.  The enumeration starts with all the digits 0 (which
    corresponds to all the set elements being assigned to the same 0th
    part), and ends with 0123...n, which corresponds to each set element
    being assigned to a different, singleton, part.

    This routine was rewritten to use 0-based lists while trying to
    preserve the beauty and efficiency of the original algorithm.

    Reference
    =========

    Nijenhuis, Albert and Wilf, Herbert. (1978) Combinatorial Algorithms,
    2nd Ed, p 91, algorithm "nexequ". Available online from
    http://www.math.upenn.edu/~wilf/website/CombAlgDownld.html (viewed
    November 17, 2012).

    """
    p = [0]*n
    q = [0]*n
    nc = 1
    yield nc, q
    while nc != n:
        m = n
        while 1:
            m -= 1
            i = q[m]
            if p[i] != 1:
                break
            q[m] = 0
        i += 1
        q[m] = i
        m += 1
        nc += m - n
        p[0] += n - m
        if i == nc:
            p[nc] = 0
            nc += 1
        p[i - 1] -= 1
        p[i] += 1
        yield nc, q


def multiset_partitions(multiset, m=None):
    """
    Return unique partitions of the given multiset (in list form).
    If ``m`` is None, all multisets will be returned, otherwise only
    partitions with ``m`` parts will be returned.

    If ``multiset`` is an integer, a range [0, 1, ..., multiset - 1]
    will be supplied.

    Examples
    ========

    >>> from sympy.utilities.iterables import multiset_partitions
    >>> list(multiset_partitions([1, 2, 3, 4], 2))
    [[[1, 2, 3], [4]], [[1, 2, 4], [3]], [[1, 2], [3, 4]],
    [[1, 3, 4], [2]], [[1, 3], [2, 4]], [[1, 4], [2, 3]],
    [[1], [2, 3, 4]]]
    >>> list(multiset_partitions([1, 2, 3, 4], 1))
    [[[1, 2, 3, 4]]]

    Only unique partitions are returned and these will be returned in a
    canonical order regardless of the order of the input:

    >>> a = [1, 2, 2, 1]
    >>> ans = list(multiset_partitions(a, 2))
    >>> a.sort()
    >>> list(multiset_partitions(a, 2)) == ans
    True
    >>> a = range(3, 1, -1)
    >>> (list(multiset_partitions(a)) ==
    ...  list(multiset_partitions(sorted(a))))
    True

    If m is omitted then all partitions will be returned:

    >>> list(multiset_partitions([1, 1, 2]))
    [[[1, 1, 2]], [[1, 1], [2]], [[1, 2], [1]], [[1], [1], [2]]]
    >>> list(multiset_partitions([1]*3))
    [[[1, 1, 1]], [[1], [1, 1]], [[1], [1], [1]]]

    Counting
    ========

    The number of partitions of a set is given by the bell number:

    >>> from sympy import bell
    >>> len(list(multiset_partitions(5))) == bell(5) == 52
    True

    The number of partitions of length k from a set of size n is given by the
    Stirling Number of the 2nd kind:

    >>> def S2(n, k):
    ...     from sympy import Dummy, binomial, factorial, Sum
    ...     if k > n:
    ...         return 0
    ...     j = Dummy()
    ...     arg = (-1)**(k-j)*j**n*binomial(k,j)
    ...     return 1/factorial(k)*Sum(arg,(j,0,k)).doit()
    ...
    >>> S2(5, 2) == len(list(multiset_partitions(5, 2))) == 15
    True

    These comments on counting apply to *sets*, not multisets.

    Notes
    =====

    When all the elements are the same in the multiset, the order
    of the returned partitions is determined by the ``partitions``
    routine. If one is counting partitions then it is better to use
    the ``nT`` function.

    See Also
    ========
    partitions
    sympy.combinatorics.partitions.Partition
    sympy.combinatorics.partitions.IntegerPartition
    sympy.functions.combinatorial.numbers.nT
    """

    if type(multiset) is int:
        n = multiset
        if m and m > n:
            return
        multiset = range(multiset)
        if m == 1:
            yield [multiset[:]]
            return
        for nc, q in _set_partitions(n):
            if m is None or nc == m:
                rv = [[] for i in range(nc)]
                for i in range(n):
                    rv[q[i]].append(multiset[i])
                yield rv
        return

    if len(multiset) == 1 and type(multiset) is str:
        multiset = [multiset]

    if not has_variety(multiset):
        n = len(multiset)
        if m and m > n:
            return
        if m == 1:
            yield [multiset[:]]
            return
        x = multiset[:1]
        for size, p in partitions(n, m, size=True):
            if m is None or size == m:
                rv = []
                for k in sorted(p):
                    rv.extend([x*k]*p[k])
                yield rv
    else:
        multiset = list(ordered(multiset))
        n = len(multiset)
        if m and m > n:
            return
        if m == 1:
            yield [multiset[:]]
            return

        # if there are repeated elements, sort them and define the
        # canon dictionary that will be used to create the cache key
        # in case elements of the multiset are not hashable
        cache = set()
        canon = {}  # {physical position: position where it appeared first}
        for i, mi in enumerate(multiset):
            canon.setdefault(i, canon.get(i, multiset.index(mi)))
        if len(set(canon.values())) != n:
            canon = {}
            for i, mi in enumerate(multiset):
                canon.setdefault(i, canon.get(i, multiset.index(mi)))
        else:
            canon = None

        for nc, q in _set_partitions(n):
            if m is None or nc == m:
                rv = [[] for i in range(nc)]
                for i in range(n):
                    rv[q[i]].append(i)
                if canon:
                    canonical = tuple(
                        sorted([tuple([canon[i] for i in j]) for j in rv]))
                    if canonical in cache:
                        continue
                    cache.add(canonical)

                yield [[multiset[j] for j in i] for i in rv]


def partitions(n, m=None, k=None, size=False):
    """Generate all partitions of integer n (>= 0).

    Parameters
    ==========

    ``m`` : integer (default gives partitions of all sizes)
        limits number of parts in parition (mnemonic: m, maximum parts)
    ``k`` : integer (default gives partitions number from 1 through n)
        limits the numbers that are kept in the partition (mnemonic: k, keys)
    ``size`` : bool (default False, only partition is returned)
        when ``True`` then (M, P) is returned where M is the sum of the
        multiplicities and P is the generated partition.

    Each partition is represented as a dictionary, mapping an integer
    to the number of copies of that integer in the partition.  For example,
    the first partition of 4 returned is {4: 1}, "4: one of them".

    Examples
    ========

    >>> from sympy.utilities.iterables import partitions

    The numbers appearing in the partition (the key of the returned dict)
    are limited with k:

    >>> for p in partitions(6, k=2):
    ...     print p
    {2: 3}
    {1: 2, 2: 2}
    {1: 4, 2: 1}
    {1: 6}

    The maximum number of parts in the partion (the sum of the values in
    the returned dict) are limited with m:

    >>> for p in partitions(6, m=2):
    ...     print p
    ...
    {6: 1}
    {1: 1, 5: 1}
    {2: 1, 4: 1}
    {3: 2}

    Note that the _same_ dictionary object is returned each time.
    This is for speed:  generating each partition goes quickly,
    taking constant time, independent of n.

    >>> [p for p in partitions(6, k=2)]
    [{1: 6}, {1: 6}, {1: 6}, {1: 6}]

    If you want to build a list of the returned dictionaries then
    make a copy of them:

    >>> [p.copy() for p in partitions(6, k=2)]
    [{2: 3}, {1: 2, 2: 2}, {1: 4, 2: 1}, {1: 6}]
    >>> [(M, p.copy()) for M, p in partitions(6, k=2, size=True)]
    [(3, {2: 3}), (4, {1: 2, 2: 2}), (5, {1: 4, 2: 1}), (6, {1: 6})]

    Reference:
        modified from Tim Peter's version to allow for k and m values:
        code.activestate.com/recipes/218332-generator-for-integer-partitions/

    See Also
    ========
    sympy.combinatorics.partitions.Partition
    sympy.combinatorics.partitions.IntegerPartition

    """
    if n < 0:
        raise ValueError("n must be >= 0")
    if m == 0:
        raise ValueError("m must be > 0")
    m = min(m or n, n)
    if m < 1:
        raise ValueError("maximum numbers in partition, m, must be > 0")
    k = min(k or n, n)
    if k < 1:
        raise ValueError("maximum value in partition, k, must be > 0")

    if m*k < n:
        return

    n, m, k = as_int(n), as_int(m), as_int(k)
    q, r = divmod(n, k)
    ms = {k: q}
    keys = [k]  # ms.keys(), from largest to smallest
    if r:
        ms[r] = 1
        keys.append(r)
    room = m - q - bool(r)
    if size:
        yield sum(ms.values()), ms
    else:
        yield ms

    while keys != [1]:
        # Reuse any 1's.
        if keys[-1] == 1:
            del keys[-1]
            reuse = ms.pop(1)
            room += reuse
        else:
            reuse = 0

        while 1:
            # Let i be the smallest key larger than 1.  Reuse one
            # instance of i.
            i = keys[-1]
            newcount = ms[i] = ms[i] - 1
            reuse += i
            if newcount == 0:
                del keys[-1], ms[i]
            room += 1

            # Break the remainder into pieces of size i-1.
            i -= 1
            q, r = divmod(reuse, i)
            need = q + bool(r)
            if need > room:
                if not keys:
                    return
                continue

            ms[i] = q
            keys.append(i)
            if r:
                ms[r] = 1
                keys.append(r)
            break
        room -= need
        if size:
            yield sum(ms.values()), ms
        else:
            yield ms


def binary_partitions(n):
    """
    Generates the binary partition of n.

    A binary partition consists only of numbers that are
    powers of two. Each step reduces a 2**(k+1) to 2**k and
    2**k. Thus 16 is converted to 8 and 8.

    Reference: TAOCP 4, section 7.2.1.5, problem 64

    Examples
    ========

    >>> from sympy.utilities.iterables import binary_partitions
    >>> for i in binary_partitions(5):
    ...     print i
    ...
    [4, 1]
    [2, 2, 1]
    [2, 1, 1, 1]
    [1, 1, 1, 1, 1]
    """
    from math import ceil, log
    pow = int(2**(ceil(log(n, 2))))
    sum = 0
    partition = []
    while pow:
        if sum + pow <= n:
            partition.append(pow)
            sum += pow
        pow >>= 1

    last_num = len(partition) - 1 - (n & 1)
    while last_num >= 0:
        yield partition
        if partition[last_num] == 2:
            partition[last_num] = 1
            partition.append(1)
            last_num -= 1
            continue
        partition.append(1)
        partition[last_num] >>= 1
        x = partition[last_num + 1] = partition[last_num]
        last_num += 1
        while x > 1:
            if x <= len(partition) - last_num - 1:
                del partition[-x + 1:]
                last_num += 1
                partition[last_num] = x
            else:
                x >>= 1
    yield [1]*n


def has_dups(seq):
    """Return True if there are any duplicate elements in ``seq``.

    Examples
    ========

    >>> from sympy.utilities.iterables import has_dups
    >>> from sympy import Dict, Set

    >>> has_dups((1, 2, 1))
    True
    >>> has_dups(range(3))
    False
    >>> all(has_dups(c) is False for c in (set(), Set(), dict(), Dict()))
    True
    """
    if isinstance(seq, (dict, set, C.Dict, C.Set)):
        return False
    uniq = set()
    return any(True for s in seq if s in uniq or uniq.add(s))


def has_variety(seq):
    """Return True if there are any different elements in ``seq``.

    Examples
    ========

    >>> from sympy.utilities.iterables import has_variety

    >>> has_variety((1, 2, 1))
    True
    >>> has_variety((1, 1, 1))
    False
    """
    for i, s in enumerate(seq):
        if i == 0:
            sentinel = s
        else:
            if s != sentinel:
                return True
    return False


def uniq(seq, result=None):
    """
    Yield unique elements from ``seq`` as an iterator. The second
    parameter ``result``  is used internally; it is not necessary to pass
    anything for this.

    Examples
    ========

    >>> from sympy.utilities.iterables import uniq
    >>> dat = [1, 4, 1, 5, 4, 2, 1, 2]
    >>> type(uniq(dat)) in (list, tuple)
    False

    >>> list(uniq(dat))
    [1, 4, 5, 2]
    >>> list(uniq(x for x in dat))
    [1, 4, 5, 2]
    >>> list(uniq([[1], [2, 1], [1]]))
    [[1], [2, 1]]
    """
    try:
        seen = set()
        result = result or []
        for i, s in enumerate(seq):
            if not (s in seen or seen.add(s)):
                yield s
    except TypeError:
        if s not in result:
            yield s
            result.append(s)
        if hasattr(seq, '__getitem__'):
            for s in uniq(seq[i + 1:], result):
                yield s
        else:
            for s in uniq(seq, result):
                yield s


def generate_bell(n):
    """
    Generates the bell permutations of length ``n``.

    Examples
    ========

    >>> from sympy.utilities.iterables import generate_bell
    >>> from sympy import zeros, Matrix
    >>> from sympy.core.compatibility import permutations

    This is the sort of permutation used in the ringing of physical bells,
    and does not produce permutations in lexicographical order. Rather, the
    permutations differ from each other by exactly one inversion, and the
    position at which the swapping occurs varies periodically in a simple
    fashion. Consider the first few permutations of 4 elements generated
    by ``permutations`` and ``generate_bell``:

    >>> list(permutations(range(4)))[:5]
    [(0, 1, 2, 3), (0, 1, 3, 2), (0, 2, 1, 3), (0, 2, 3, 1), (0, 3, 1, 2)]
    >>> list(generate_bell(4))[:5]
    [(0, 1, 2, 3), (1, 0, 2, 3), (1, 2, 0, 3), (1, 2, 3, 0), (2, 1, 3, 0)]

    Notice how the 2nd and 3rd lexicographical permutations have 3 elements
    out of place whereas each bell permutations always has only two
    elements out of place relative to the previous permutation.

    How the position of inversion varies across the elements can be seen
    by tracing out where the 0 appears in the permutations:

    >>> m = zeros(4, 24)
    >>> for i, p in enumerate(generate_bell(4)):
    ...     m[:, i] = Matrix(list(p))
    >>> m.print_nonzero('X')
    [ XXXXXX  XXXXXX  XXXXXX ]
    [X XXXX XX XXXX XX XXXX X]
    [XX XX XXXX XX XXXX XX XX]
    [XXX  XXXXXX  XXXXXX  XXX]

    References
    ==========

    * http://en.wikipedia.org/wiki/Method_ringing
    * http://stackoverflow.com/questions/4856615/recursive-permutation/4857018
    * http://programminggeeks.com/bell-algorithm-for-permutation/
    * http://en.wikipedia.org/wiki/
      Steinhaus%E2%80%93Johnson%E2%80%93Trotter_algorithm
    * Generating involutions, derangements, and relatives by ECO
      Vincent Vajnovszki, DMTCS vol 1 issue 12, 2010

    """
    from sympy.functions.combinatorial.factorials import factorial
    pos = dir = 1
    do = factorial(n)
    p = range(n)
    yield tuple(p)
    do -= 1
    while do:
        if pos >= n:
            dir = -dir
            p[0], p[1] = p[1], p[0]
        elif pos < 1:
            dir = -dir
            p[-2], p[-1] = p[-1], p[-2]
        else:
            p[pos - 1], p[pos] = p[pos], p[pos - 1]
        pos += dir
        yield tuple(p)
        do -= 1


def generate_involutions(n):
    """
    Generates involutions.

    An involution is a permutation that when multiplied
    by itself equals the identity permutation. In this
    implementation the involutions are generated using
    Fixed Points.

    Alternatively, an involution can be considered as
    a permutation that does not contain any cycles with
    a length that is greater than two.

    Reference:
    http://mathworld.wolfram.com/PermutationInvolution.html

    Examples
    ========

    >>> from sympy.utilities.iterables import generate_involutions
    >>> list(generate_involutions(3))
    [(0, 1, 2), (0, 2, 1), (1, 0, 2), (2, 1, 0)]
    >>> len(list(generate_involutions(4)))
    10
    """
    idx = range(n)
    for p in permutations(idx):
        for i in idx:
            if p[p[i]] != i:
                break
        else:
            yield p


def generate_derangements(perm):
    """
    Routine to generate unique derangements.

    TODO: This will be rewritten to use the
    ECO operator approach once the permutations
    branch is in master.

    Examples
    ========

    >>> from sympy.utilities.iterables import generate_derangements
    >>> list(generate_derangements([0, 1, 2]))
    [[1, 2, 0], [2, 0, 1]]
    >>> list(generate_derangements([0, 1, 2, 3]))
    [[1, 0, 3, 2], [1, 2, 3, 0], [1, 3, 0, 2], [2, 0, 3, 1], \
    [2, 3, 0, 1], [2, 3, 1, 0], [3, 0, 1, 2], [3, 2, 0, 1], \
    [3, 2, 1, 0]]
    >>> list(generate_derangements([0, 1, 1]))
    []

    See Also
    ========
    sympy.functions.combinatorial.factorials.subfactorial
    """
    p = multiset_permutations(perm)
    indices = range(len(perm))
    p0 = next(p)
    for pi in p:
        if all(pi[i] != p0[i] for i in indices):
            yield pi


@deprecated(
    useinstead="bracelets", deprecated_since_version="0.7.3")
def unrestricted_necklace(n, k):
    """Wrapper to necklaces to return a free (unrestricted) necklace."""
    return necklaces(n, k, free=True)


def necklaces(n, k, free=False):
    """
    A routine to generate necklaces that may (free=True) or may not
    (free=False) be turned over to be viewed. The "necklaces" returned
    are comprised of ``n`` integers (beads) with ``k`` different
    values (colors). Only unique necklaces are returned.

    Examples
    ========

    >>> from sympy.utilities.iterables import necklaces, bracelets
    >>> def show(s, i):
    ...     return ''.join(s[j] for j in i)

    The "unrestricted necklace" is sometimes also referred to as a
    "bracelet" (an object that can be turned over, a sequence that can
    be reversed) and the term "necklace" is used to imply a sequence
    that cannot be reversed. So ACB == ABC for a bracelet (rotate and
    reverse) while the two are different for a necklace since rotation
    alone cannot make the two sequences the same.

    (mnemonic: Bracelets can be viewed Backwards, but Not Necklaces.)

    >>> B = [show('ABC', i) for i in bracelets(3, 3)]
    >>> N = [show('ABC', i) for i in necklaces(3, 3)]
    >>> set(N) - set(B)
    set(['ACB'])

    >>> list(necklaces(4, 2))
    [(0, 0, 0, 0), (0, 0, 0, 1), (0, 0, 1, 1),
     (0, 1, 0, 1), (0, 1, 1, 1), (1, 1, 1, 1)]

    >>> [show('.o', i) for i in bracelets(4, 2)]
    ['....', '...o', '..oo', '.o.o', '.ooo', 'oooo']

    References
    ==========

    http://mathworld.wolfram.com/Necklace.html

    """
    return uniq(minlex(i, directed=not free) for i in
        variations(range(k), n, repetition=True))


def bracelets(n, k):
    """Wrapper to necklaces to return a free (unrestricted) necklace."""
    return necklaces(n, k, free=True)


def generate_oriented_forest(n):
    """
    This algorithm generates oriented forests.

    An oriented graph is a directed graph having no symmetric pair of directed
    edges. A forest is an acyclic graph, i.e., it has no cycles. A forest can
    also be described as a disjoint union of trees, which are graphs in which
    any two vertices are connected by exactly one simple path.

    Reference:
    [1] T. Beyer and S.M. Hedetniemi: constant time generation of \
        rooted trees, SIAM J. Computing Vol. 9, No. 4, November 1980
    [2] http://stackoverflow.com/questions/1633833/oriented-forest-taocp-algorithm-in-python

    Examples
    ========

    >>> from sympy.utilities.iterables import generate_oriented_forest
    >>> list(generate_oriented_forest(4))
    [[0, 1, 2, 3], [0, 1, 2, 2], [0, 1, 2, 1], [0, 1, 2, 0], \
    [0, 1, 1, 1], [0, 1, 1, 0], [0, 1, 0, 1], [0, 1, 0, 0], [0, 0, 0, 0]]
    """
    P = range(-1, n)
    while True:
        yield P[1:]
        if P[n] > 0:
            P[n] = P[P[n]]
        else:
            for p in xrange(n - 1, 0, -1):
                if P[p] != 0:
                    target = P[p] - 1
                    for q in xrange(p - 1, 0, -1):
                        if P[q] == target:
                            break
                    offset = p - q
                    for i in xrange(p, n + 1):
                        P[i] = P[i - offset]
                    break
            else:
                break


def minlex(seq, directed=True, is_set=False, small=None):
    """
    Return a tuple where the smallest element appears first; if
    ``directed`` is True (default) then the order is preserved, otherwise
    the sequence will be reversed if that gives a smaller ordering.

    If every element appears only once then is_set can be set to True
    for more efficient processing.

    If the smallest element is known at the time of calling, it can be
    passed and the calculation of the smallest element will be omitted.

    Examples
    ========

    >>> from sympy.combinatorics.polyhedron import minlex
    >>> minlex((1, 2, 0))
    (0, 1, 2)
    >>> minlex((1, 0, 2))
    (0, 2, 1)
    >>> minlex((1, 0, 2), directed=False)
    (0, 1, 2)

    >>> minlex('11010011000', directed=True)
    '00011010011'
    >>> minlex('11010011000', directed=False)
    '00011001011'

    """
    is_str = isinstance(seq, str)
    seq = list(seq)
    if small is None:
        small = min(seq)
    if is_set:
        i = seq.index(small)
        if not directed:
            n = len(seq)
            p = (i + 1) % n
            m = (i - 1) % n
            if seq[p] > seq[m]:
                seq = list(reversed(seq))
                i = n - i - 1
        if i:
            seq = rotate_left(seq, i)
        best = seq
    else:
        count = seq.count(small)
        if count == 1 and directed:
            best = rotate_left(seq, seq.index(small))
        else:
            # if not directed, and not a set, we can't just
            # pass this off to minlex with is_set True since
            # peeking at the neighbor may not be sufficient to
            # make the decision so we continue...
            best = seq
            for i in range(count):
                seq = rotate_left(seq, seq.index(small, count != 1))
                if seq < best:
                    best = seq
                # it's cheaper to rotate now rather than search
                # again for these in reversed order so we test
                # the reverse now
                if not directed:
                    seq = rotate_left(seq, 1)
                    seq = list(reversed(seq))
                    if seq < best:
                        best = seq
                    seq = list(reversed(seq))
                    seq = rotate_right(seq, 1)
    # common return
    if is_str:
        return ''.join(best)
    return tuple(best)


def runs(seq, op=gt):
    """Group the sequence into lists in which successive elements
    all compare the same with the comparison operator, ``op``:
    op(seq[i + 1], seq[i]) is True from all elements in a run.

    Examples
    ========

    >>> from sympy.utilities.iterables import runs
    >>> from operator import ge
    >>> runs([0, 1, 2, 2, 1, 4, 3, 2, 2])
    [[0, 1, 2], [2], [1, 4], [3], [2], [2]]
    >>> runs([0, 1, 2, 2, 1, 4, 3, 2, 2], op=ge)
    [[0, 1, 2, 2], [1, 4], [3], [2, 2]]
    """
    cycles = []
    seq = iter(seq)
    try:
        run = [seq.next()]
    except StopIteration:
        return []
    while True:
        try:
            ei = seq.next()
        except StopIteration:
            break
        if op(ei, run[-1]):
            run.append(ei)
            continue
        else:
            cycles.append(run)
            run = [ei]
    if run:
        cycles.append(run)
    return cycles


def kbins(l, k, ordered=None):
    """
    Return sequence ``l`` partitioned into ``k`` bins.

    Examples
    ========

    >>> from sympy.utilities.iterables import kbins

    The default is to give the items in the same order, but grouped
    into k partitions without any reordering:

    >>> for p in kbins(range(5), 2):
    ...     print p
    ...
    [[0], [1, 2, 3, 4]]
    [[0, 1], [2, 3, 4]]
    [[0, 1, 2], [3, 4]]
    [[0, 1, 2, 3], [4]]

    The ``ordered`` flag which is either None (to give the simple partition
    of the the elements) or is a 2 digit integer indicating whether the order of
    the bins and the order of the items in the bins matters. Given::

        A = [[0], [1, 2]]
        B = [[1, 2], [0]]
        C = [[2, 1], [0]]
        D = [[0], [2, 1]]

    the following values for ``ordered`` have the shown meanings::

        00 means A == B == C == D
        01 means A == B
        10 means A == D
        11 means A == A

    >>> for ordered in [None, 0, 1, 10, 11]:
    ...     print 'ordered =', ordered
    ...     for p in kbins(range(3), 2, ordered=ordered):
    ...         print '    ', p
    ...
    ordered = None
         [[0], [1, 2]]
         [[0, 1], [2]]
    ordered = 0
         [[0, 1], [2]]
         [[0, 2], [1]]
         [[0], [1, 2]]
    ordered = 1
         [[0], [1, 2]]
         [[0], [2, 1]]
         [[1], [0, 2]]
         [[1], [2, 0]]
         [[2], [0, 1]]
         [[2], [1, 0]]
    ordered = 10
         [[0, 1], [2]]
         [[2], [0, 1]]
         [[0, 2], [1]]
         [[1], [0, 2]]
         [[0], [1, 2]]
         [[1, 2], [0]]
    ordered = 11
         [[0], [1, 2]]
         [[0, 1], [2]]
         [[0], [2, 1]]
         [[0, 2], [1]]
         [[1], [0, 2]]
         [[1, 0], [2]]
         [[1], [2, 0]]
         [[1, 2], [0]]
         [[2], [0, 1]]
         [[2, 0], [1]]
         [[2], [1, 0]]
         [[2, 1], [0]]

    See Also
    ========
    partitions, multiset_partitions

    """
    def partition(lista, bins):
        #  EnricoGiampieri's partition generator from
        #  http://stackoverflow.com/questions/13131491/
        #  partition-n-items-into-k-bins-in-python-lazily
        if len(lista) == 1 or bins == 1:
            yield [lista]
        elif len(lista) > 1 and bins > 1:
            for i in range(1, len(lista)):
                for part in partition(lista[i:], bins - 1):
                    if len([lista[:i]] + part) == bins:
                        yield [lista[:i]] + part

    if ordered is None:
        for p in partition(l, k):
            yield p
    elif ordered == 11:
        for pl in multiset_permutations(l):
            pl = list(pl)
            for p in partition(pl, k):
                yield p
    elif ordered == 00:
        for p in multiset_partitions(l, k):
            yield p
    elif ordered == 10:
        for p in multiset_partitions(l, k):
            for perm in permutations(p):
                yield list(perm)
    elif ordered == 01:
        for kgot, p in partitions(len(l), k, size=True):
            if kgot != k:
                continue
            for li in multiset_permutations(l):
                rv = []
                i = j = 0
                li = list(li)
                for size, multiplicity in sorted(p.items()):
                    for m in range(multiplicity):
                        j = i + size
                        rv.append(li[i: j])
                        i = j
                yield rv
    else:
        raise ValueError(
            'ordered must be one of 00, 01, 10 or 11, not %s' % ordered)
