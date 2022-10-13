"""PyAPI API client."""
from __future__ import annotations

from string import Formatter
from typing import Any, cast, Mapping, Optional, Sequence, Union
from urllib.parse import urlencode, urlsplit, urlunsplit

import httpx
from openapi_core.validation.request.datatypes import (
    Headers,
    ImmutableMultiDict,
    RequestParameters,
)
from openapi_core.validation.request.protocols import Request as RequestProtocol
from openapi_core.validation.response.protocols import Response as ResponseProtocol

from .utils import OperationSpec


def prepare_request_params(
    host_url: str,
    op_spec: OperationSpec,
    path_params: Optional[Sequence[str]] = None,
    query_params: Optional[Mapping] = None,
    body: Optional[Union[dict, list]] = None,
    headers: Optional[Mapping] = None,
) -> Mapping[str, Any]:
    """
    Creates the mapping of all parameters needed to build a request.

    Args:
        host_url: The server the request is made to.
        op_spec: Operation specification as defined in the spec.
        path_params: Path parameters of the request, if any.
        query_params: Query parameters of the request, if any.
        body: Body of the request, if present.
        headers: Custom headers of the request, if any.

    Returns:
        A mapping of request parameters.

    Raises:
        Runtime error if the provided arguments are not compatible
        with the operation spec.
    """
    url_parts = urlsplit(host_url)
    if path_params is None:
        path_params = []
    if headers is None:
        headers = {}

    formatter = Formatter()
    url_vars = [var for _, var, _, _ in formatter.parse(op_spec.path) if var is not None]
    path_pattern = url_parts.path + op_spec.path

    len_vars = len(url_vars)
    if len(path_params) != len_vars:
        error_message = f"Incorrect arguments: {op_spec.operation_id} accepts"
        if len_vars:
            error_message += (
                f" {len_vars} positional argument{'s' if len_vars > 1 else ''}:"
                f" {', '.join(url_vars)}"
            )
        else:
            error_message += " no positional arguments"
        raise RuntimeError(error_message)

    content_type_header = headers.get("content-type", None)

    params = RequestParameters(
        path=dict(zip(url_vars, path_params)),
        query=query_params or {},
        header=headers or {},
        cookie={},
    )

    mimetype = "application/json"
    content = getattr(op_spec, "request_body", {}).get("content", {})
    if content and mimetype not in content:
        mimetype = list(content)[0]
    if content_type_header:
        mimetype = content_type_header

    url_dict = url_parts._asdict()
    url_dict["path"] = path_pattern.format(**params.path)
    url_dict["query"] = urlencode(params.query)
    url = urlunsplit(tuple(url_dict.values()))

    request_params = {
        "method": op_spec.method.lower(),
        "url": url,
        "headers": params.header,
    }
    if body is not None:
        request_params["json" if "json" in mimetype else "data"] = body
    return request_params


class OpenAPIRequest(RequestProtocol):
    """Wrapper for PyAPI Server requests."""

    def __init__(self, request: httpx.Request):
        self.request = request
        self.response: Optional[httpx.Response] = None
        if request.url is None:
            raise RuntimeError("Request URL is missing")

        cookie = {}
        cookie.update(self.request.headers.get("cookie", {}))
        cookie.update(self.request.headers.get("cookie2", {}))

        self.parameters = RequestParameters(
            query=ImmutableMultiDict(self.request.url.params),
            header=Headers(dict(self.request.headers)),
            cookie=ImmutableMultiDict(cookie),
        )

    @property
    def host_url(self) -> str:
        """Return the request host url."""
        return f"{self.request.url.scheme}://{self.request.url.netloc.decode()}"

    @property
    def path(self) -> str:
        """Return the request path."""
        assert isinstance(self.request.url.path, str)
        return self.request.url.path

    @property
    def method(self) -> str:
        """Return the request HTTP method."""
        method = self.request.method
        return method and method.lower() or ""

    @property
    def body(self) -> Optional[str]:
        """Return the request body as string, if present."""
        return self.request.content.decode("utf-8")

    @property
    def mimetype(self) -> str:
        """Return the request content type."""
        # Order matters because all python requests issued from a session
        # include Accept */* which does not necessarily match the content type
        return str(
            self.request.headers.get("Content-Type") or self.request.headers.get("Accept")
        )

    @classmethod
    def from_params(cls, params: Mapping[str, Any]) -> OpenAPIRequest:
        """
        Construct the request from prepared parameters.

        Args:
            params: A mapping of prepared parameters,

        Returns:
            A request object.
        """
        return cls(httpx.Request(**params))

    def send(self, client) -> ResponseProtocol:
        """
        Make the prepared request.

        Args:
            client: Client object to make the request.

        Returns:
            A response object.
        """
        self.response = cast(httpx.Response, client.send(self.request))
        self.response.raise_for_status()
        return cast(ResponseProtocol, self.openapi_response)

    @property
    def openapi_response(self) -> Optional[ResponseProtocol]:
        """Construct an OpenAPI response from the actual response."""
        return OpenAPIResponse(self.response) if self.response else None


class OpenAPIResponse(ResponseProtocol):
    """Wrapper for PyAPI Server responses."""

    def __init__(self, response: httpx.Response):
        self._response = response

    @property
    def data(self) -> str:
        """Return the response content as string."""
        return self._response.content.decode()

    @property
    def status_code(self) -> int:
        """Return the response HTTP status code."""
        return self._response.status_code

    @property
    def mimetype(self) -> str:
        """Return the response content type."""
        mimetype, *_ = self._response.headers.get("content-type", "").split(";")
        return mimetype

    @property
    def headers(self) -> Mapping[str, Any]:
        """Return the response headers."""
        return Headers(dict(self._response.headers))
