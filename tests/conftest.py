import json
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def spec_dict(config):
    file_path = config.test_dir / "openapi.json"
    with file_path.open() as spec_file:
        return json.load(spec_file)


@pytest.fixture
def yaml_spec_file(spec_dict, tmp_path):
    """A YAML copy of the JSON spec, generated on the fly (openapi.json is the source of truth)."""
    path = tmp_path / "openapi.yaml"
    path.write_text(yaml.safe_dump(spec_dict))
    return path


class Config:
    def __init__(self):
        self.test_dir = Path(__file__).parent


@pytest.fixture
def config():
    return Config()
