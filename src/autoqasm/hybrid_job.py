# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from __future__ import annotations

import functools
import inspect
import os
import tempfile
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from logging import Logger, getLogger
from pathlib import Path
from types import CodeType, ModuleType

from braket.aws.aws_session import AwsSession
from braket.jobs.config import (
    CheckpointConfig,
    InstanceConfig,
    OutputDataConfig,
    S3DataSourceConfig,
    StoppingCondition,
)
from braket.jobs.hybrid_job import (
    _create_job,
    _IncludeModules,
    _log_hyperparameters,
    _process_dependencies,
    _process_input_data,
    _serialize_entry_point,
    _validate_python_version,
)
from braket.jobs.local.local_job_container_setup import _get_env_input_data
from braket.jobs.quantum_job_creation import _generate_default_job_name

DEFAULT_INPUT_CHANNEL = "input"
INNER_SOURCE_INPUT_CHANNEL = "_braket_job_decorator_inner_function_source"
INNER_SOURCE_INPUT_FOLDER = "_inner_function_source_folder"


def hybrid_job(
    *,
    device: str | None,
    include_modules: str | ModuleType | Iterable[str | ModuleType] | None = None,
    dependencies: str | Path | list[str] | None = None,
    local: bool = False,
    job_name: str | None = None,
    image_uri: str | None = None,
    input_data: str | dict | S3DataSourceConfig | None = None,
    wait_until_complete: bool = False,
    instance_config: InstanceConfig | None = None,
    distribution: str | None = None,
    copy_checkpoints_from_job: str | None = None,
    checkpoint_config: CheckpointConfig | None = None,
    role_arn: str | None = None,
    stopping_condition: StoppingCondition | None = None,
    output_data_config: OutputDataConfig | None = None,
    aws_session: AwsSession | None = None,
    tags: dict[str, str] | None = None,
    logger: Logger = getLogger(__name__),
    quiet: bool | None = None,
    reservation_arn: str | None = None,
) -> Callable:
    """Defines a hybrid job by decorating the entry point function. The job will be created
    when the decorated function is called.

    The job created will be a `LocalQuantumJob` when `local` is set to `True`, otherwise an
    `AwsQuantumJob`. The following parameters will be ignored when running a job with
    `local` set to `True`: `wait_until_complete`, `instance_config`, `distribution`,
    `copy_checkpoints_from_job`, `stopping_condition`, `tags`, `logger`, and `quiet`.

    Remarks:
        Hybrid jobs created using this decorator have limited access to the source code of
        functions defined outside of the decorated function. Functionality that depends on
        source code analysis may not work properly when referencing functions defined outside
        of the decorated function.

    Args:
        device (str | None): Device ARN of the QPU device that receives priority quantum
            task queueing once the hybrid job begins running. Each QPU has a separate hybrid jobs
            queue so that only one hybrid job is running at a time. The device string is accessible
            in the hybrid job instance as the environment variable "AMZN_BRAKET_DEVICE_ARN".
            When using embedded simulators, you may provide the device argument as string of the
            form: "local:<provider>/<simulator_name>" or `None`.

        include_modules (str | ModuleType | Iterable[str | ModuleType] | None): Either a
            single module or module name or a list of module or module names referring to local
            modules to be included. Any references to members of these modules in the hybrid job
            algorithm code will be serialized as part of the algorithm code. Default: `[]`

        dependencies (str | Path | list[str] | None): Path (absolute or relative) to a
            requirements.txt file, or alternatively a list of strings, with each string being a
            `requirement specifier <https://pip.pypa.io/en/stable/reference/requirement-specifiers/
            #requirement-specifiers>`_, to be used for the hybrid job.

        local (bool): Whether to use local mode for the hybrid job. Default: `False`

        job_name (str | None): A string that specifies the name with which the job is created.
            Allowed pattern for job name: `^[a-zA-Z0-9](-*[a-zA-Z0-9]){0,50}$`. Defaults to
            f'{decorated-function-name}-{timestamp}'.

        image_uri (str | None): A str that specifies the ECR image to use for executing the job.
            `retrieve_image()` function may be used for retrieving the ECR image URIs
            for the containers supported by Braket. Default: `<Braket base image_uri>`.

        input_data (str | dict | S3DataSourceConfig | None): Information about the training
            data. Dictionary maps channel names to local paths or S3 URIs. Contents found
            at any local paths will be uploaded to S3 at
            f's3://{default_bucket_name}/jobs/{job_name}/data/{channel_name}'. If a local
            path, S3 URI, or S3DataSourceConfig is provided, it will be given a default
            channel name "input".
            Default: {}.

        wait_until_complete (bool): `True` if we should wait until the job completes.
            This would tail the job logs as it waits. Otherwise `False`. Ignored if using
            local mode. Default: `False`.

        instance_config (InstanceConfig | None): Configuration of the instance(s) for running the
            classical code for the hybrid job. Default:
            `InstanceConfig(instanceType='ml.m5.large', instanceCount=1, volumeSizeInGB=30)`.

        distribution (str | None): A str that specifies how the job should be distributed.
            If set to "data_parallel", the hyperparameters for the job will be set to use data
            parallelism features for PyTorch or TensorFlow. Default: `None`.

        copy_checkpoints_from_job (str | None): A str that specifies the job ARN whose
            checkpoint you want to use in the current job. Specifying this value will copy
            over the checkpoint data from `use_checkpoints_from_job`'s checkpoint_config
            s3Uri to the current job's checkpoint_config s3Uri, making it available at
            checkpoint_config.localPath during the job execution. Default: `None`

        checkpoint_config (CheckpointConfig | None): Configuration that specifies the
            location where checkpoint data is stored.
            Default: `CheckpointConfig(localPath='/opt/jobs/checkpoints',
            s3Uri=f's3://{default_bucket_name}/jobs/{job_name}/checkpoints')`.

        role_arn (str | None): A str providing the IAM role ARN used to execute the
            script. Default: IAM role returned by AwsSession's `get_default_jobs_role()`.

        stopping_condition (StoppingCondition | None): The maximum length of time, in seconds,
            and the maximum number of tasks that a job can run before being forcefully stopped.
            Default: StoppingCondition(maxRuntimeInSeconds=5 * 24 * 60 * 60).

        output_data_config (OutputDataConfig | None): Specifies the location for the output of
            the job.
            Default: `OutputDataConfig(s3Path=f's3://{default_bucket_name}/jobs/{job_name}/data',
            kmsKeyId=None)`.

        aws_session (AwsSession | None): AwsSession for connecting to AWS Services.
            Default: AwsSession()

        tags (dict[str, str] | None): Dict specifying the key-value pairs for tagging this job.
            Default: {}.

        logger (Logger): Logger object with which to write logs, such as task statuses
            while waiting for task to be in a terminal state. Default: `getLogger(__name__)`

        quiet (bool | None): Sets the verbosity of the logger to low and does not report queue
            position. Default is `False`.

        reservation_arn (str | None): the reservation window arn provided by Braket
            Direct to reserve exclusive usage for the device to run the hybrid job on.
            Default: None.

    Returns:
        Callable: the callable for creating a Hybrid Job.
    """
    _validate_python_version(image_uri, aws_session)

    def _hybrid_job(entry_point: Callable) -> Callable:
        @functools.wraps(entry_point)
        def job_wrapper(*args, **kwargs) -> Callable:
            """
            The job wrapper.
            Returns:
                Callable: the callable for creating a Hybrid Job.
            """
            with (
                _IncludeModules(include_modules),
                tempfile.TemporaryDirectory(dir="", prefix="decorator_job_") as temp_dir,
                persist_inner_function_source(entry_point) as inner_source_input,
            ):
                if input_data is None:
                    job_input_data = inner_source_input
                elif isinstance(input_data, dict):
                    if INNER_SOURCE_INPUT_CHANNEL in input_data:
                        raise ValueError(f"input channel cannot be {INNER_SOURCE_INPUT_CHANNEL}")
                    job_input_data = {**input_data, **inner_source_input}
                else:
                    job_input_data = {DEFAULT_INPUT_CHANNEL: input_data, **inner_source_input}

                temp_dir_path = Path(temp_dir)
                entry_point_file_path = Path("entry_point.py")
                with open(temp_dir_path / entry_point_file_path, "w") as entry_point_file:
                    template = "\n".join(
                        [
                            _process_input_data(input_data),
                            _serialize_entry_point(entry_point, args, kwargs),
                        ]
                    )
                    entry_point_file.write(template)

                if dependencies:
                    _process_dependencies(dependencies, temp_dir_path)

                job_args = {
                    "device": device or "local:none/none",
                    "source_module": temp_dir,
                    "entry_point": (
                        f"{temp_dir}.{entry_point_file_path.stem}:{entry_point.__name__}"
                    ),
                    "wait_until_complete": wait_until_complete,
                    "job_name": job_name or _generate_default_job_name(func=entry_point),
                    "hyperparameters": _log_hyperparameters(entry_point, args, kwargs),
                    "logger": logger,
                }
                optional_args = {
                    "image_uri": image_uri,
                    "input_data": job_input_data,
                    "instance_config": instance_config,
                    "distribution": distribution,
                    "checkpoint_config": checkpoint_config,
                    "copy_checkpoints_from_job": copy_checkpoints_from_job,
                    "role_arn": role_arn,
                    "stopping_condition": stopping_condition,
                    "output_data_config": output_data_config,
                    "aws_session": aws_session,
                    "tags": tags,
                    "quiet": quiet,
                    "reservation_arn": reservation_arn,
                }
                for key, value in optional_args.items():
                    if value is not None:
                        job_args[key] = value

                job = _create_job(job_args, local)
            return job

        return job_wrapper

    return _hybrid_job


@contextmanager
def persist_inner_function_source(entry_point: callable) -> None:
    """Persist the source code of the cloudpickled function by saving its source code as input data
    and replace the source file path with the saved one.

    Args:
        entry_point (callable): The job decorated function.
    """
    inner_source_mapping = _get_inner_function_source(entry_point.__code__)

    with tempfile.TemporaryDirectory() as temp_dir:
        copy_dir = f"{temp_dir}/{INNER_SOURCE_INPUT_FOLDER}"
        os.mkdir(copy_dir)
        path_mapping = _save_inner_source_to_file(inner_source_mapping, copy_dir)
        entry_point.__code__ = _replace_inner_function_source_path(
            entry_point.__code__, path_mapping
        )
        yield {INNER_SOURCE_INPUT_CHANNEL: copy_dir}


def _replace_inner_function_source_path(
    code_object: CodeType, path_mapping: dict[str, str]
) -> CodeType:
    """Recursively replace source code file path of the code object and of its child node's code
    objects.

    Args:
        code_object (CodeType): Code object which source code file path to be replaced.
        path_mapping (dict[str, str]): Mapping between local file path to path in a job
            environment.

    Returns:
        CodeType: Code object with the source code file path replaced
    """
    new_co_consts = []
    for const in code_object.co_consts:
        if inspect.iscode(const):
            new_path = path_mapping[const.co_filename]
            const = const.replace(co_filename=new_path)
            const = _replace_inner_function_source_path(const, path_mapping)
        new_co_consts.append(const)

    code_object = code_object.replace(co_consts=tuple(new_co_consts))
    return code_object


def _save_inner_source_to_file(inner_source: dict[str, str], input_data_dir: str) -> dict[str, str]:
    """Saves the source code as input data for a job and returns a dictionary that maps the local
    source file path of a function to the one to be used in the job environment.

    Args:
        inner_source (dict[str, str]): Mapping between source file name and source code.
        input_data_dir (str): The path of the folder to be uploaded to job as input data.

    Returns:
        dict[str, str]: Mapping between local file path to path in a job environment.
    """
    path_mapping = {}
    for i, (local_path, source_code) in enumerate(inner_source.items()):
        copy_file_name = f"source_{i}.py"
        with open(f"{input_data_dir}/{copy_file_name}", "w") as f:
            f.write(source_code)

        path_mapping[local_path] = os.path.join(
            _get_env_input_data()["AMZN_BRAKET_INPUT_DIR"],
            INNER_SOURCE_INPUT_CHANNEL,
            copy_file_name,
        )
    return path_mapping


def _get_inner_function_source(code_object: CodeType) -> dict[str, str]:
    """Returns a dictionary that maps the source file name to source code for all source files
    used by the inner functions inside the job decorated function.
    Args:
        code_object (CodeType): Code object of a inner function.
    Returns:
        dict[str, str]: Mapping between source file name and source code.
    """
    inner_source = {}
    for const in code_object.co_consts:
        if inspect.iscode(const):
            source_file_path = inspect.getfile(code_object)
            lines, _ = inspect.findsource(code_object)
            inner_source.update({source_file_path: "".join(lines)})
            inner_source.update(_get_inner_function_source(const))
    return inner_source
