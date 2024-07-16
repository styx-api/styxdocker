""".. include:: ../../README.md"""  # noqa: D415

import logging
import os
import pathlib
import pathlib as pl
import re
import shlex
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from subprocess import PIPE, Popen

from styxdefs import Execution, InputPathType, Metadata, OutputPathType, Runner


def _docker_mount(host_path: str, container_path: str, readonly: bool) -> str:
    """Construct Docker mount argument."""
    host_path = host_path.replace('"', r"\"")
    container_path = container_path.replace('"', r"\"")
    host_path = host_path.replace("\\", "\\\\")
    container_path = container_path.replace("\\", "\\\\")
    readonly_str = ",readonly" if readonly else ""
    return f"type=bind,source={host_path},target={container_path}{readonly_str}"


class StyxDockerError(Exception):
    """Styx Docker error."""

    def __init__(
        self,
        return_code: int | None = None,
        docker_args: list[str] | None = None,
        command_args: list[str] | None = None,
    ) -> None:
        """Create StyxDockerError."""
        message = "Command failed."

        if return_code is not None:
            message += f"\n- Return code: {return_code}"

        if docker_args is not None:
            message += f"\n- Docker args: {shlex.join(docker_args)}"

        if command_args is not None:
            message += f"\n- Command args: {shlex.join(command_args)}"

        super().__init__(message)


class _DockerExecution(Execution):
    """Docker execution."""

    def __init__(
        self,
        logger: logging.Logger,
        output_dir: pathlib.Path,
        metadata: Metadata,
        container_tag: str,
        docker_executable: str,
    ) -> None:
        """Create DockerExecution."""
        self.logger: logging.Logger = logger
        self.input_files: list[tuple[pl.Path, str]] = []
        self.input_file_next_id = 0
        self.output_files: list[tuple[pl.Path, str]] = []
        self.output_file_next_id = 0
        self.output_dir = output_dir
        self.metadata = metadata
        self.container_tag = container_tag
        self.docker_executable = docker_executable

    def input_file(self, host_file: InputPathType) -> str:
        """Resolve input file."""
        _host_file = pl.Path(host_file)
        local_file = f"/styx_input/{self.input_file_next_id}/{_host_file.name}"
        self.input_file_next_id += 1
        self.input_files.append((_host_file, local_file))
        return local_file

    def output_file(self, local_file: str, optional: bool = False) -> OutputPathType:
        """Resolve output file."""
        return self.output_dir / local_file

    def run(self, cargs: list[str]) -> None:
        """Execute."""
        mounts: list[str] = []

        for i, (host_file, local_file) in enumerate(self.input_files):
            mounts.append("--mount")
            mounts.append(
                _docker_mount(
                    host_file.absolute().as_posix(), local_file, readonly=True
                )
            )

        # Output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create run script
        run_script = self.output_dir / "run.sh"
        # Ensure utf-8 encoding and unix newlines
        run_script.write_text(
            f"#!/bin/bash\n{shlex.join(cargs)}\n", encoding="utf-8", newline="\n"
        )

        mounts.append("--mount")
        mounts.append(
            _docker_mount(
                self.output_dir.absolute().as_posix(), "/styx_output", readonly=False
            )
        )

        docker_extra_args: list[str] = []
        container = self.metadata.container_image_tag

        if container is None:
            raise ValueError("No container image tag specified in metadata")

        docker_command = [
            self.docker_executable,
            "run",
            "--rm",
            "-w",
            "/styx_output",
            *mounts,
            "--entrypoint",
            "/bin/bash",
            *docker_extra_args,
            container,
            "./run.sh",
        ]

        self.logger.debug(f"Running docker: {shlex.join(docker_command)}")
        self.logger.debug(f"Running command: {shlex.join(cargs)}")

        def _stdout_handler(line: str) -> None:
            self.logger.info(line)

        def _stderr_handler(line: str) -> None:
            self.logger.error(line)

        time_start = datetime.now()
        with Popen(docker_command, text=True, stdout=PIPE, stderr=PIPE) as process:
            with ThreadPoolExecutor(2) as pool:  # two threads to handle the streams
                exhaust = partial(pool.submit, partial(deque, maxlen=0))
                exhaust(_stdout_handler(line[:-1]) for line in process.stdout)  # type: ignore
                exhaust(_stderr_handler(line[:-1]) for line in process.stderr)  # type: ignore
        return_code = process.poll()
        time_end = datetime.now()
        self.logger.info(f"Executed {self.metadata.name} in {time_end - time_start}")
        if return_code:
            raise StyxDockerError(return_code, docker_command, cargs)


def _default_execution_output_dir(metadata: Metadata) -> pl.Path:
    """Default output dir generator."""
    filesafe_name = re.sub(r"\W+", "_", metadata.name)
    return pl.Path(f"output_{filesafe_name}")


class DockerRunner(Runner):
    """Docker runner."""

    logger_name = "styx_docker_runner"

    def __init__(
        self,
        image_overrides: dict[str, str] | None = None,
        docker_executable: str = "docker",
        data_dir: InputPathType | None = None,
    ) -> None:
        """Create a new DockerRunner."""
        self.data_dir = pathlib.Path(data_dir or "styx_tmp")
        self.uid = os.urandom(8).hex()
        self.execution_counter = 0
        self.docker_executable = docker_executable
        self.image_overrides = image_overrides or {}

        # Configure logger
        self.logger = logging.getLogger(self.logger_name)
        if not self.logger.hasHandlers():
            self.logger.setLevel(logging.DEBUG)
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            formatter = logging.Formatter("[%(levelname).1s] %(message)s")
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

    def start_execution(self, metadata: Metadata) -> Execution:
        """Start execution."""
        if metadata.container_image_tag is None:
            raise ValueError("No container image tag specified in metadata")
        container_tag = self.image_overrides.get(
            metadata.container_image_tag, metadata.container_image_tag
        )
        self.execution_counter += 1
        return _DockerExecution(
            logger=self.logger,
            output_dir=self.data_dir
            / f"{self.uid}_{self.execution_counter - 1}_{metadata.name}",
            metadata=metadata,
            container_tag=container_tag,
            docker_executable=self.docker_executable,
        )
