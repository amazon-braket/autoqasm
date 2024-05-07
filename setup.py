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

from setuptools import find_namespace_packages, setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="autoqasm",
    version="0.0.1.dev0",
    license="Apache License 2.0",
    python_requires=">= 3.9",
    packages=find_namespace_packages(where="src", exclude=("test",)),
    package_dir={"": "src"},
    install_requires=[
        # Pin the latest commit of feature/autoqasm branch of amazon-braket/amazon-braket-sdk-python.git  # noqa E501
        "amazon-braket-sdk @ git+https://github.com/amazon-braket/amazon-braket-sdk-python.git@d62e288961af1b9a42b14667e1167fca301e2708#egg=amazon-braket-sdk",  # noqa E501
        # Pin the latest commit of mcm-sim branch of amazon-braket/amazon-braket-default-simulator-python.git  # noqa E501
        # to get the version of the simulator that supports the mcm=True argument for Monte Carlo
        # simulation of mid-circuit measurement, which AutoQASM requires.
        # NOTE: This is currently installed automatically due to feature/autoqasm requirements
        # "amazon-braket-default-simulator @ git+https://github.com/amazon-braket/amazon-braket-default-simulator-python.git@ab068c860963c29842d7649c741f88da669597eb#egg=amazon-braket-default-simulator",  # noqa E501
        "oqpy~=0.3.5",
        "diastatic-malt",
        "numpy",
        "openpulse",
        "openqasm3",
        "sympy",
        "astunparse",
        "gast",
        "termcolor",
        "openqasm_pygments",
    ],
    extras_require={
        "test": [
            "black",
            "botocore",
            "flake8<=5.0.4",
            "isort",
            "jsonschema==3.2.0",
            "pre-commit",
            "pylint",
            "pytest",
            "pytest-cov",
            "pytest-rerunfailures",
            "pytest-xdist[psutil]",
            "sphinx",
            "sphinx-rtd-theme",
            "sphinxcontrib-apidoc",
            "tox",
        ],
    },
    include_package_data=True,
    url="https://github.com/amazon-braket/autoqasm",
    author="Amazon Web Services",
    description=("Python-native programming library for developing quantum programs"),
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="Amazon AWS Braket Quantum",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
