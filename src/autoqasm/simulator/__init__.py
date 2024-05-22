# Copyright Amazon.com Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""
This module contains a local simulator implementation which can be used to
simulate AutoQASM programs at the full OpenQASM 3.0 scope of functionality,
including programs which contain mid-circuit measurement and classical control flow.

The recommended usage of this simulator is by instantiating the Braket LocalSimulator
object with the "autoqasm" backend:

.. code-block:: python

    import autoqasm as aq
    from braket.devices import LocalSimulator

    @aq.main
    def bell_state():
        h(0)
        cnot(0, 1)
        return measure([0, 1])

    device = LocalSimulator("autoqasm")
    result = device.run(bell_state, shots=100).result()
"""

from .simulator import McmSimulator  # noqa: F401
