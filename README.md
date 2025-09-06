# Docker Runner for Styx compiled wrappers

[![Build](https://github.com/styx-api/styxdocker/actions/workflows/test.yaml/badge.svg?branch=main)](https://github.com/styx-api/styxdocker/actions/workflows/test.yaml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/styx-api/styxdocker/branch/main/graph/badge.svg?token=22HWWFWPW5)](https://codecov.io/gh/styx-api/styxdocker)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![stability-stable](https://img.shields.io/badge/stability-stable-green.svg)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/styx-api/styxdocker/blob/main/LICENSE)
[![pages](https://img.shields.io/badge/api-docs-blue)](https://styx-api.github.io/styxdocker)

`styxdocker` is a Python package that provides Docker integration for Styx compiled wrappers. It allows you to run Styx functions within Docker containers, offering improved isolation and reproducibility for your workflows.

## Installation
You can install `styxdocker` using pip:

```bash
pip install styxdocker
```

## Usage

Here's a basic example of how to use styxdocker:

```Python
from styxdefs import set_global_runner
from styxdocker import DockerRunner

# Initialize the DockerRunner
runner = DockerRunner()

# Set the global runner for Styx
set_global_runner(runner)

# Now you can use any Styx functions as usual, and they will run in Docker containers
```

## Advanced Configuration
The `DockerRunner` class accepts several parameters for advanced configuration:

- `image_overrides`: A dictionary to override container image tags
- `docker_executable`: Path to the Docker executable (default: "docker")
- `user_id`: User ID to run the container as (default: current user ID on POSIX systems)
- `data_dir`: Directory for temporary data storage
- `environ`: Environment variables to set in the container

Example:
```python
runner = DockerRunner(
    image_overrides={"python:3.9": "my-custom-python:3.9"},
    docker_executable="/usr/local/bin/docker",
    user_id=1000,
    data_dir="/tmp/styx_data",
    environ={"PYTHONPATH": "/app/lib"}
)
```

## Error Handling

`styxdocker` provides a custom error class, `StyxDockerError`, which is raised when a Docker execution fails. This error includes details about the return code, command arguments, and Docker arguments for easier debugging.

## Cross-Platform Support

`styxdocker` is designed to work on Linux, macOS, and Windows. On POSIX systems (Linux and macOS), it automatically uses the current user's ID for running containers, ensuring proper file permissions. On Windows, this feature is not available, but the package remains functional.

## Contributing

Contributions to `styxdocker` are welcome! Please refer to the [GitHub repository](https://github.com/styx-api/styxdocker) for information on how to contribute, report issues, or submit pull requests.

## License

`styxdocker` is released under the MIT License. See the LICENSE file for details.

## Documentation

For detailed API documentation, please visit our [API Docs](https://styx-api.github.io/styxdocker).

## Support

If you encounter any issues or have questions, please open an issue on the [GitHub repository](https://github.com/styx-api/styxdocker).

## Requirements

- Python 3.10+
- Docker installed and running on your system

## Comparison with [`styxsingularity`](https://github.com/styx-api/styxsingularity)

While [`styxdocker`](https://github.com/styx-api/styxdocker) and [`styxsingularity`](https://github.com/styx-api/styxsingularity) serve similar purposes, they have some key differences:

- Container Technology: `styxdocker` uses Docker, while `styxsingularity` uses Singularity/Apptainer.
- Platform Support: `styxdocker` works on Windows, Linux, and macOS, whereas `styxsingularity` is not supported on Windows.
- User Permissions: `styxdocker` can run containers as the current user on POSIX systems, which can help with file permission issues.

Choose the package that best fits your infrastructure and requirements.
