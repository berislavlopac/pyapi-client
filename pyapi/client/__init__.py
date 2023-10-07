"""PyAPI Client."""
from __future__ import annotations

from pathlib import Path
from typing import MutableSequence, Tuple, Type

import httpx
from openapi_core import protocols, Spec, validate_request, validate_response
from stringcase import snakecase

from .spec import get_spec_from_file, OperationSpec
from .wrappers import HttpxClient, HttpxRequest, HttpxResponse, Requestable

HistoricRecord = Tuple[protocols.Request, protocols.Response]


class Client:
    """PyAPI client class."""

    def __init__(
        self,
        spec: Spec | dict,
        *,
        server_url: str = "",
        client: Requestable | None = None,
        request_class: Type[protocols.Request] = HttpxRequest,
        response_class: Type[protocols.Response] = HttpxResponse,
        headers: dict | None = None,
    ):
        if isinstance(spec, dict):
            spec = Spec.from_dict(spec)
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

        for operation_id, op_spec in OperationSpec.get_all(spec).items():
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
        spec = get_spec_from_file(Path(path))
        return cls(spec, **kwargs)

    @property
    def latest(self) -> HistoricRecord | None:
        """Returns the latest request/response pair.

        Returns None if no requests were made successfully.
        """
        return self.request_history[-1] if self.request_history else None
