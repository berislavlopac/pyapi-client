"""Utility classes and functions."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from enum import Enum
from itertools import chain

import yaml
from jsonschema_path import SchemaPath
from stringcase import camelcase


def _parameters(spec: SchemaPath) -> list:
    """Returns the raw list of parameters from a spec section, or an empty list."""
    parameters: SchemaPath | list = spec.get("parameters", [])
    return parameters.read_value() if isinstance(parameters, SchemaPath) else parameters


class OperationSpec:
    """Utility class for defining API operations."""

    def __init__(
        self,
        path: str,
        method: str,
        spec: SchemaPath | dict,
        parameters: Mapping | Sequence | None = None,
    ):
        self.path = path
        self.method = method
        self.spec = spec
        self.parameters: dict = {}
        if isinstance(parameters, Sequence):
            self.parameters = defaultdict(dict)
            for param in parameters:
                self.parameters["in"]["name"] = param
            self.parameters = dict(self.parameters)

    def __getattr__(self, name):
        """
        Looks for values of the specification fields.

        If the exact match of a name fails, also checks for the camel case version.
        """
        if name in self.spec:
            return self.spec[name]
        if (camelcase_name := camelcase(name)) in self.spec:
            return self.spec[camelcase_name]
        return super().__getattribute__(name)

    @classmethod
    def get_all(cls, spec: SchemaPath) -> dict[str, OperationSpec]:
        """Builds a dict of all operations in the spec."""
        return {
            str(op_spec["operationId"]): cls(
                str(path),
                str(method),
                op_spec,
                _parameters(path_spec) + _parameters(op_spec),
            )
            for path, path_spec in spec["paths"].items()
            for method, op_spec in path_spec.items()
            if "operationId" in op_spec
        }


class SpecFormat(tuple, Enum):
    """Supported spec file extensions."""

    JSON = ("json",)
    YAML = ("yaml", "yml")


class UnknownSpecFormatError(TypeError):
    """Error when the format spec is unknown."""

    def __init__(self):
        message = (
            f"Unknown specification format. Accepted formats: {', '.join(chain(*SpecFormat))}"
        )
        super().__init__(message)


def load_spec(raw_spec: str, spec_format: SpecFormat) -> dict:
    """Loads the raw spec based on the format."""
    if spec_format == SpecFormat.JSON:
        load: Callable = json.loads
    else:
        load = yaml.safe_load
    return load(raw_spec)
