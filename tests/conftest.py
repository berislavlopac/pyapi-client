import json
import subprocess
import time
from pathlib import Path

import pytest


@pytest.fixture
def spec_dict(config):
    file_path = config.test_dir / "openapi.json"
    with file_path.open() as spec_file:
        return json.load(spec_file)


class Config:
    def __init__(self):
        self.test_dir = Path(__file__).parent
        # self.endpoint_base = "tests.endpoints"


@pytest.fixture
def config():
    return Config()


@pytest.fixture  # (autouse=True, scope="function")
def app():
    app_process = subprocess.Popen(
        [
            "uvicorn",
            "tests.application:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            # "--log-level",
            # "debug",
        ]
    )
    time.sleep(1)
    yield app_process
    app_process.terminate()
