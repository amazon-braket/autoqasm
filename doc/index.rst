########################
AutoQASM
########################

**AutoQASM is not an officially supported AWS product.**

This experimental module offers a new quantum-imperative programming experience embedded in Python
for developing quantum programs. AutoQASM is *experimental* software. We may change, remove, or
deprecate parts of the AutoQASM API without notice. The name AutoQASM is a working title and is
also subject to change.

This documentation provides information about the AutoQASM library. The project
is hosted on GitHub at https://github.com/amazon-braket/autoqasm. The project
includes the source code, installation instructions, and other information.

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   decorators
   hybrid_jobs

.. toctree::
   :maxdepth: 2
   :caption: Examples

   Getting Started with AutoQASM <examples/1_Getting_started_with_AutoQASM>
   Expressing Classical Control Flow <examples/2_Expressing_classical_control_flow>
   Iterative Phase Estimation <examples/3_1_Iterative_phase_estimation>
   Magic State Distillation <examples/3_2_magic_state_distillation>
   Native Programming <examples/4_Native_programming>
   Pulse Programming and Dynamical Decoupling <examples/5_Pulse_programming_and_dynamical_decoupling>
   Customize Gate Calibrations <examples/6_Customize_gate_calibrations>

.. toctree::
   :maxdepth: 2
   :caption: Architecture

   variable_capture_and_assignment

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   _apidoc/modules
