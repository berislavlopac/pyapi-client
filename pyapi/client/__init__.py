"""PyAPI Client."""
from functools import partial
from pathlib import Path
from types import ModuleType
from typing import Any, MutableSequence, Optional, Protocol, Tuple, Type, Union

import httpx
from openapi_core import Spec
from openapi_core.validation.request import openapi_request_validator
from openapi_core.validation.request.protocols import Request as RequestProtocol
from openapi_core.validation.response import openapi_response_validator
from openapi_core.validation.response.protocols import Response as ResponseProtocol
from stringcase import snakecase

from .utils import get_spec_from_file, OperationSpec
from .validation import OpenAPIRequest, OpenAPIResponse, prepare_request_params


class Requestable(Protocol):  # pragma: no cover
    """Defines the `request` method compatible with the `requests` library."""

    def request(self, method: str, url: str, **kwargs) -> Any:
        """Construct and send a `Request`."""
        ...


class Client:
    """PyAPI client class."""

    def __init__(
        self,
        spec: Union[Spec, dict],
        *,
        server_url: Optional[str] = None,
        client: Optional[Requestable] = None,
        request_class: Type[RequestProtocol] = OpenAPIRequest,
        response_class: Type[ResponseProtocol] = OpenAPIResponse,
        headers: Optional[dict] = None,
    ):
        if isinstance(spec, dict):
            spec = Spec.from_dict(spec)
        self.spec = spec
        self.client = client or httpx.Client()
        self.request_class = request_class
        self.response_class = response_class
        self.common_headers = headers or {}
        self.request_history: MutableSequence[Tuple[RequestProtocol, ResponseProtocol]] = []

        if server_url is None:
            server_url = self.spec["servers"][0]["url"]
        else:
            server_url = server_url.rstrip("/")
            for server in self.spec["servers"]:
                if server_url == server["url"]:
                    break
            else:
                self.spec["servers"].append({"url": server_url})
        self.server_url = server_url
        self.validate = partial(openapi_response_validator.validate, spec=self.spec)

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
            body_: Optional[Union[dict, list]] = None,
            headers_: Optional[dict] = None,
            **kwargs,
        ):
            headers = self.common_headers.copy()
            headers.update(headers_ or {})
            request_params = prepare_request_params(
                self.server_url, op_spec, args, kwargs, body=body_, headers=headers
            )
            request = self.request_class.from_params(request_params)
            openapi_request_validator.validate(self.spec, request).raise_for_errors()

            response = request.send(self.client)
            self.request_history.append((request, response))
            openapi_response_validator.validate(self.spec, request, response).raise_for_errors()
            return response

        operation.__doc__ = op_spec.spec.get("summary") or op_spec.operation_id
        if description := op_spec.spec.get("description"):
            operation.__doc__ = f"{ operation.__doc__ }\n\n{ description }"
        return operation

    @classmethod
    def from_file(cls, path: Union[Path, str], **kwargs):
        """Creates an instance of the class by loading the spec from a local file."""
        spec = get_spec_from_file(path)
        return cls(spec, **kwargs)

    @property
    def latest(self) -> Optional[Tuple[RequestProtocol, ResponseProtocol]]:
        """Returns the latest request/response pair.

        Returns None if no requests were made successfully.
        """
        return self.request_history[-1] if self.request_history else None
