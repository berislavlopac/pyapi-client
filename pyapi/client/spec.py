"""Utility classes and functions."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence

# from collections.abc import Mapping, Sequence
from enum import Enum
from itertools import chain

import yaml
from jsonschema_path import SchemaPath
from stringcase import camelcase


class OperationSpec:
    """Utility class for defining API operations."""

    def __init__(
        self, path: str, method: str, spec: dict, parameters: Mapping | Sequence | None = None
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
            op_spec["operationId"]: cls(
                path,
                method,
                op_spec,
                path_spec.get("parameters", []) + op_spec.get("parameters", []),
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
    def __init__(self):
        message = (
            "Unknown specification format."
            f" Accepted formats: {', '.join(chain(*SpecFormat))}"
        )
        super().__init__(message)


def load_spec(raw_spec: str, spec_format: SpecFormat) -> dict:
    if spec_format == SpecFormat.JSON:
        load: Callable = json.loads
    else:
        load = yaml.safe_load
    return load(raw_spec)
