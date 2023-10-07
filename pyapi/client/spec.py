"""Utility classes and functions."""
from __future__ import annotations

import json
from collections import defaultdict
from enum import Enum
from itertools import chain
from pathlib import Path
from typing import Callable, Dict, Mapping, Sequence, TYPE_CHECKING

import yaml
from stringcase import camelcase

if TYPE_CHECKING:  # pragma: no cover
    from . import Spec


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
                self.parameters[param.pop("in")][param.pop("name")] = param
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
    def get_all(cls, spec: Spec) -> Dict[str, OperationSpec]:
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


class SpecFileTypes(tuple, Enum):
    """Supported spec file extensions."""

    JSON = ("json",)
    YAML = ("yaml", "yml")


def get_spec_from_file(path: Path) -> dict:
    """Loads a local file and creates an OpenAPI `Spec` object."""
    suffix = path.suffix[1:].lower()

    if suffix in SpecFileTypes.JSON:
        spec_load: Callable = json.load
    elif suffix in SpecFileTypes.YAML:
        spec_load = yaml.safe_load
    else:
        raise RuntimeError(
            f"Unknown specification file type."
            f" Accepted types: {', '.join(chain(*SpecFileTypes))}"
        )

    with open(path, encoding="utf-8") as spec_file:
        return spec_load(spec_file)
