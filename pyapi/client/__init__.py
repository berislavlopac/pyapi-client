"""PyAPI Client."""

from __future__ import annotations

from collections.abc import MutableSequence
from json import JSONDecodeError
from pathlib import Path

import httpx
from jsonschema_path import SchemaPath
from openapi_core import protocols, validate_request, validate_response
from stringcase import snakecase

from .spec import load_spec, OperationSpec, SpecFormat, UnknownSpecFormatError
from .wrappers import HttpxClient, HttpxRequest, HttpxResponse, Requestable

HistoricRecord = tuple[protocols.Request, protocols.Response]


class Client:
    """PyAPI client class."""

    def __init__(
        self,
        spec: SchemaPath | dict,
        *,
        server_url: str = "",
        client: Requestable | None = None,
        request_class: type[protocols.Request] = HttpxRequest,
        response_class: type[protocols.Response] = HttpxResponse,
        headers: dict | None = None,
    ):
        if isinstance(spec, dict):
            self.spec = SchemaPath.from_dict(spec)
        else:
            self.spec = spec
        self.client = client or httpx.Client()
        self.request_class = request_class
        self.response_class = response_class
        self.common_headers = headers or {}
        self.request_history: MutableSequence[HistoricRecord] = []

        if not server_url:
            server_url = self.spec["servers"][0]["url"]
        else:
            server_url = server_url.rstrip("/")
            for server in self.spec["servers"]:
                if server_url == server["url"]:
                    break
            else:
                self.spec["servers"].append({"url": server_url})
        self.server_url = server_url

        for operation_id, op_spec in OperationSpec.get_all(self.spec).items():
            setattr(
                self,
                snakecase(operation_id),
                self._get_operation(op_spec).__get__(self),
            )

    @staticmethod
    def _get_operation(op_spec: OperationSpec):
        # TODO: extract args and kwargs from operation parameters
        def operation(
            self,
            *args,
            body_: dict | list | None = None,
            headers_: dict | None = None,
            **kwargs,
        ) -> protocols.Response:
            headers = self.common_headers.copy()
            headers.update(headers_ or {})
            request = self.request_class.from_params(
                self.server_url, op_spec, args, kwargs, body=body_, headers=headers
            )
            validate_request(request=request, spec=self.spec)
            response = request.send(self.client)
            self.request_history.append((request, response))

            validate_response(request=request, response=HttpxResponse(response), spec=self.spec)

            return HttpxResponse(response)

        operation.__doc__ = op_spec.spec.get("summary") or op_spec.operation_id
        if description := op_spec.spec.get("description"):
            operation.__doc__ = f"{ operation.__doc__ }\n\n{ description }"
        return operation

    @classmethod
    def from_file(cls, path: Path | str, **kwargs):
        """Creates an instance of the class by loading the spec from a local file."""
        path = Path(path)
        suffix = path.suffix[1:].lower()

        for spec_format in SpecFormat:
            if suffix in spec_format:
                break
        else:
            raise UnknownSpecFormatError()
        source = path.read_text(encoding="utf-8")

        spec = load_spec(source, spec_format)
        return cls(spec, **kwargs)

    @classmethod
    def from_url(cls, url: str, **kwargs):
        """Creates an instance of the class by loading the spec from a URL."""
        response = httpx.get(url)
        try:
            raw_spec = response.json()
            spec_format = SpecFormat.JSON
        except JSONDecodeError:
            raw_spec = response.text
            spec_format = SpecFormat.YAML
        spec = load_spec(raw_spec, spec_format)
        return cls(spec, **kwargs)

    @property
    def latest(self) -> HistoricRecord | None:
        """Returns the latest request/response pair.

        Returns None if no requests were made successfully.
        """
        return self.request_history[-1] if self.request_history else None
