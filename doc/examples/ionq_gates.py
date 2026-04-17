import numpy as np

import autoqasm as aq
from autoqasm.instructions import gpi, gpi2, zz


@aq.gate
def h(q: aq.Qubit):
    gpi2(q, np.pi / 2)
    gpi(q, 0)


@aq.gate
def u(q: aq.Qubit, a: float, b: float, c: float):
    gpi2(q, a)
    gpi(q, b)
    gpi2(q, c)


@aq.gate
def rx(q: aq.Qubit, theta: float):
    u(q, np.pi / 2, theta / 2 + np.pi / 2, np.pi / 2)


@aq.gate
def ry(q: aq.Qubit, theta: float):
    u(q, np.pi, theta / 2 + np.pi, np.pi)


@aq.gate
def xx(q0: aq.Qubit, q1: aq.Qubit, theta: float):
    h(q0)
    h(q1)
    zz(q0, q1, theta)
    h(q0)
    h(q1)


@aq.gate
def cnot(q0: aq.Qubit, q1: aq.Qubit):
    ry(q0, np.pi / 2)
    xx(q0, q1, np.pi / 2)
    rx(q0, -np.pi / 2)
    rx(q1, -np.pi / 2)
    ry(q0, -np.pi / 2)
