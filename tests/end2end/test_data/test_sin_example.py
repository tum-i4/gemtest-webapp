import math

import gemtest as gmt
from gemtest.relations import approximately

data = range(-10, 10)

A = gmt.create_metamorphic_relation('A', data, relation=approximately)


@gmt.transformation(A)
@gmt.randomized('n', gmt.RandInt(1, 10))
@gmt.fixed('c', 0)
def shift(source_input: float, n: int, c: int) -> float:
    return source_input + 2 * n * math.pi + c


@gmt.system_under_test()
def test_sin(input_float: float, **_kwargs) -> float:
    return math.sin(input_float)
