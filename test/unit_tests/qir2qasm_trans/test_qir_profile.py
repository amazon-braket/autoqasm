import tempfile
import os
import textwrap

import pyqir
import pytest

from autoqasm.qir2qasm_trans.qir_trans.qir_profile import Profile
from autoqasm.qir2qasm_trans.qir_trans.translator import Exporter


def test_qir_profile():
    pfl = Profile(name = 'test')
    