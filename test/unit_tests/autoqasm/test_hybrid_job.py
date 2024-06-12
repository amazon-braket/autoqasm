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

"""Tests for the hybrid_job module."""

import inspect
import sys
import tempfile
from logging import getLogger
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from braket.aws import AwsQuantumJob
from braket.devices import Devices
from braket.jobs.local import LocalQuantumJob

import autoqasm as aq


@pytest.fixture
def aws_session():
    aws_session = MagicMock()
    python_version_str = f"py{sys.version_info.major}{sys.version_info.minor}"
    aws_session.get_full_image_tag.return_value = f"1.0-cpu-{python_version_str}-ubuntu22.04"
    aws_session.region = "us-west-2"
    return aws_session


@patch("builtins.open", new_callable=mock_open)
@patch.object(sys.modules["os"], "mkdir")
@patch.object(sys.modules["braket.jobs.hybrid_job"], "retrieve_image")
@patch("time.time", return_value=123.0)
@patch("tempfile.TemporaryDirectory")
@patch.object(LocalQuantumJob, "create")
def test_decorator_persist_inner_function_source(
    mock_create, mock_tempdir, mock_time, mock_retrieve, mock_mkdir, mock_file, aws_session
):
    from autoqasm.hybrid_job import INNER_SOURCE_INPUT_CHANNEL, INNER_SOURCE_INPUT_FOLDER

    mock_retrieve.return_value = "00000000.dkr.ecr.us-west-2.amazonaws.com/latest"

    def my_entry():
        def inner_function_1():
            def inner_function_2():
                return "my inner function 2"

            return "my inner function 1"

        return inner_function_1

    inner1 = my_entry()

    mock_tempdir_name = "job_temp_dir_00000"
    mock_tempdir.return_value.__enter__.return_value = mock_tempdir_name

    device = Devices.Amazon.SV1
    source_module = mock_tempdir_name
    entry_point = f"{mock_tempdir_name}.entry_point:my_entry"

    my_entry = aq.hybrid_job(device=Devices.Amazon.SV1, local=True, aws_session=aws_session)(
        my_entry
    )
    my_entry()

    expected_source = "".join(inspect.findsource(inner1)[0])
    assert mock_file().write.call_args_list[0][0][0] == expected_source

    expect_source_path = f"{mock_tempdir_name}/{INNER_SOURCE_INPUT_FOLDER}/source_0.py"
    assert mock_file.call_args_list[0][0][0] == expect_source_path

    mock_create.assert_called_with(
        device=device,
        source_module=source_module,
        entry_point=entry_point,
        job_name="my-entry-123000",
        hyperparameters={},
        aws_session=aws_session,
        input_data={INNER_SOURCE_INPUT_CHANNEL: f"{mock_tempdir_name}/{INNER_SOURCE_INPUT_FOLDER}"},
    )
    assert mock_tempdir.return_value.__exit__.called


@patch.object(sys.modules["autoqasm.hybrid_job"], "persist_inner_function_source")
@patch.object(sys.modules["braket.jobs.hybrid_job"], "retrieve_image")
@patch("time.time", return_value=123.0)
@patch("builtins.open")
@patch("tempfile.TemporaryDirectory")
@patch.object(AwsQuantumJob, "create")
def test_decorator_conflict_channel_name(
    mock_create,
    mock_tempdir,
    _mock_open,
    mock_time,
    mock_retrieve,
    mock_persist_source,
    aws_session,
):
    from autoqasm.hybrid_job import INNER_SOURCE_INPUT_CHANNEL

    mock_retrieve.return_value = "00000000.dkr.ecr.us-west-2.amazonaws.com/latest"

    @aq.hybrid_job(
        device=None, aws_session=aws_session, input_data={INNER_SOURCE_INPUT_CHANNEL: "foo-bar"}
    )
    def my_entry(c=0, d: float = 1.0, **extras):
        return "my entry return value"

    mock_tempdir_name = "job_temp_dir_00000"
    mock_tempdir.return_value.__enter__.return_value = mock_tempdir_name
    mock_persist_source.return_value.__enter__.return_value = {}

    expect_error_message = f"input channel cannot be {INNER_SOURCE_INPUT_CHANNEL}"
    with pytest.raises(ValueError, match=expect_error_message):
        my_entry()


@patch.object(sys.modules["autoqasm.hybrid_job"], "persist_inner_function_source")
@patch("braket.jobs.image_uris.retrieve_image")
@patch("sys.stdout")
@patch("time.time", return_value=123.0)
@patch("cloudpickle.register_pickle_by_value")
@patch("cloudpickle.unregister_pickle_by_value")
@patch("shutil.copy")
@patch("builtins.open")
@patch.object(AwsQuantumJob, "create")
def test_decorator_non_defaults(
    mock_create,
    _mock_open,
    mock_copy,
    mock_register,
    mock_unregister,
    mock_time,
    mock_stdout,
    mock_retrieve,
    mock_persist_source,
):
    mock_retrieve.return_value = "should-not-be-used"
    dependencies = "my_requirements.txt"
    image_uri = "my_image.uri"
    distribution = "data_parallel"
    copy_checkpoints_from_job = "arn/other-job"
    role_arn = "role_arn"
    aws_session = MagicMock()
    tags = {"my_tag": "my_value"}
    reservation_arn = (
        "arn:aws:braket:us-west-2:123456789123:reservation/a1b123cd-45e6-789f-gh01-i234567jk8l9"
    )
    logger = getLogger(__name__)

    with tempfile.TemporaryDirectory() as tempdir:
        Path(tempdir, "temp_dir").mkdir()
        Path(tempdir, "temp_file").touch()

        input_data = {
            "my_prefix": "my_input_data",
            "my_dir": Path(tempdir, "temp_dir"),
            "my_file": Path(tempdir, "temp_file"),
            "my_s3_prefix": "s3://bucket/path/to/prefix",
        }

        @aq.hybrid_job(
            device=Devices.Amazon.SV1,
            dependencies=dependencies,
            image_uri=image_uri,
            input_data=input_data,
            wait_until_complete=True,
            distribution=distribution,
            copy_checkpoints_from_job=copy_checkpoints_from_job,
            role_arn=role_arn,
            aws_session=aws_session,
            tags=tags,
            reservation_arn=reservation_arn,
            logger=logger,
        )
        def my_entry(a, b: int, c=0, d: float = 1.0, **extras) -> str:
            return "my entry return value"

        mock_tempdir = MagicMock(spec=tempfile.TemporaryDirectory)
        mock_tempdir_name = "job_temp_dir_00000"
        mock_tempdir.__enter__.return_value = mock_tempdir_name
        mock_persist_source.return_value.__enter__.return_value = {}

        device = Devices.Amazon.SV1
        source_module = mock_tempdir_name
        entry_point = f"{mock_tempdir_name}.entry_point:my_entry"
        wait_until_complete = True

        s3_not_linked = (
            "Input data channels mapped to an S3 source will not be available in the working "
            'directory. Use `get_input_data_dir(channel="my_s3_prefix")` to read input data '
            "from S3 source inside the job container."
        )

        with patch("tempfile.TemporaryDirectory", return_value=mock_tempdir):
            my_entry("a", 2, 3, 4, extra_param="value", another=6)

    mock_create.assert_called_with(
        device=device,
        source_module=source_module,
        entry_point=entry_point,
        image_uri=image_uri,
        input_data=input_data,
        wait_until_complete=wait_until_complete,
        job_name="my-entry-123000",
        distribution=distribution,
        hyperparameters={
            "a": "a",
            "b": "2",
            "c": "3",
            "d": "4",
            "extra_param": "value",
            "another": "6",
        },
        copy_checkpoints_from_job=copy_checkpoints_from_job,
        role_arn=role_arn,
        aws_session=aws_session,
        tags=tags,
        logger=logger,
        reservation_arn=reservation_arn,
    )
    mock_copy.assert_called_with(
        Path("my_requirements.txt").resolve(), Path(mock_tempdir_name, "requirements.txt")
    )
    assert mock_tempdir.__exit__.called
    mock_stdout.write.assert_any_call(s3_not_linked)


@patch.object(sys.modules["autoqasm.hybrid_job"], "persist_inner_function_source")
@patch.object(sys.modules["braket.jobs.hybrid_job"], "retrieve_image")
@patch("time.time", return_value=123.0)
@patch("builtins.open")
@patch("tempfile.TemporaryDirectory")
@patch.object(AwsQuantumJob, "create")
def test_decorator_non_dict_input(
    mock_create,
    mock_tempdir,
    _mock_open,
    mock_time,
    mock_retrieve,
    mock_persist_source,
    aws_session,
):
    mock_retrieve.return_value = "00000000.dkr.ecr.us-west-2.amazonaws.com/latest"
    input_prefix = "my_input"

    @aq.hybrid_job(device=None, input_data=input_prefix, aws_session=aws_session)
    def my_entry():
        return "my entry return value"

    mock_tempdir_name = "job_temp_dir_00000"
    mock_tempdir.return_value.__enter__.return_value = mock_tempdir_name
    mock_persist_source.return_value.__enter__.return_value = {}

    source_module = mock_tempdir_name
    entry_point = f"{mock_tempdir_name}.entry_point:my_entry"
    wait_until_complete = False

    device = "local:none/none"

    my_entry()

    mock_create.assert_called_with(
        device=device,
        source_module=source_module,
        entry_point=entry_point,
        wait_until_complete=wait_until_complete,
        job_name="my-entry-123000",
        hyperparameters={},
        logger=getLogger("autoqasm.hybrid_job"),
        input_data={"input": input_prefix},
        aws_session=aws_session,
    )
    assert mock_tempdir.return_value.__exit__.called
