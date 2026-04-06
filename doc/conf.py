"""Sphinx configuration."""

import datetime
from importlib.metadata import version

from pygments.formatters import LatexFormatter

# Sphinx configuration below.
project = "autoqasm"
version = version(project)
release = version
copyright = f"{datetime.datetime.now().year}, Amazon.com"
author = "Amazon Web Services"

extensions = [
    "sphinxcontrib.apidoc",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "nbsphinx",
]

nbsphinx_execute = "never"

exclude_patterns = ["**/.ipynb_checkpoints"]

source_suffix = ".rst"
master_doc = "index"

autoclass_content = "both"
autodoc_member_order = "bysource"
default_role = "py:obj"

html_theme = "sphinx_rtd_theme"
htmlhelp_basename = f"{project}doc"

language = "en"

# LaTeX configuration
_pygments_style_defs = LatexFormatter().get_style_defs()

latex_elements = {
    "preamble": rf"""
% Define commands for Dirac notation (used in quantum computing notebooks)
\providecommand{{\ket}}[1]{{\left|#1\right\rangle}}
\providecommand{{\bra}}[1]{{\left\langle#1\right|}}
\providecommand{{\braket}}[2]{{\left\langle#1\middle|#2\right\rangle}}
% Pygments style definitions for syntax-highlighted code in nbsphinx cells
{_pygments_style_defs}
""",
}

napoleon_use_rtype = False

apidoc_module_dir = "../src/autoqasm"
apidoc_output_dir = "_apidoc"
apidoc_excluded_paths = ["../test"]
apidoc_separate_modules = True
apidoc_module_first = True
apidoc_extra_args = ["-f", "--implicit-namespaces", "-H", "API Reference"]
