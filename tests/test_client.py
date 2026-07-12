import json
from http import HTTPStatus
from json import JSONDecodeError

import httpx
import pytest
from jsonschema_path import SchemaPath
from openapi_core import protocols
from starlette.testclient import TestClient

from pyapi.client import Client

from .application import app


def test_client_calls_endpoint(spec_dict, config):
    client = Client(spec_dict, client=TestClient(app))
    response = client.dummy_test_endpoint()
    assert isinstance(response, protocols.Response)
    assert response.data == b'{"foo":"bar"}'


def test_client_calls_endpoint_with_body(spec_dict, config):
    client = Client(spec_dict, client=TestClient(app))
    response = client.dummy_post_endpoint(body_={"foo": "bar"})
    assert isinstance(response, protocols.Response)
    assert response.status_code == HTTPStatus.NO_CONTENT


def test_client_calls_endpoint_with_custom_headers(spec_dict, config, monkeypatch):
    client = Client(spec_dict, client=TestClient(app))

    def patch_request(request):
        def wrapper(*args, **kwargs):
            client.request_info = {"args": args, "kwargs": kwargs}
            return request(*args, **kwargs)

        return wrapper

    monkeypatch.setattr(client.client, "request", patch_request(client.client.request))
    client.dummy_test_endpoint(headers_={"foo": "bar"})

    headers = dict(client.latest[0].request.headers)
    assert all(item in headers.items() for item in {"foo": "bar"}.items())


def test_client_incorrect_args_raises_error(spec_dict, config):
    client = Client(spec_dict, client=TestClient(app))
    with pytest.raises(RuntimeError) as error:
        client.dummy_test_endpoint("foo")
    assert error.exconly() == (
        "RuntimeError: Incorrect arguments: dummyTestEndpoint accepts no positional arguments"
    )


def test_client_too_few_args_raises_error(spec_dict, config):
    client = Client(spec_dict, client=TestClient(app))
    with pytest.raises(RuntimeError) as error:
        client.dummy_test_endpoint_with_argument()
    assert error.exconly() == (
        "RuntimeError: Incorrect arguments: dummyTestEndpointWithArgument"
        " accepts 1 positional argument: test_arg"
    )


def test_unknown_server_url_gets_added_to_spec(spec_dict):
    test_server = spec_dict["servers"][1]["url"]
    client = Client(spec_dict, server_url=test_server)
    assert client.server_url == test_server


def test_known_server_url_gets_selected(spec_dict):
    client = Client(spec_dict, server_url="foo.bar")
    assert client.server_url == "foo.bar"
    assert client.spec["servers"][-1]["url"] == "foo.bar"


def test_use_first_server_url_as_default(spec_dict):
    client = Client(spec_dict)
    assert client.server_url == spec_dict["servers"][0]["url"]


def test_incorrect_endpoint_raises_error(spec_dict):
    client = Client(spec_dict)
    with pytest.raises(AttributeError):
        client.foo_bar()


def test_spec_loads_from_json_file(config):
    client = Client.from_file(config.test_dir / "openapi.json")
    assert client.spec["info"]["title"] == "Test Spec"


def test_spec_loads_from_yaml_file(yaml_spec_file):
    client = Client.from_file(yaml_spec_file)
    assert client.spec["info"]["title"] == "Test Spec"


def test_loading_from_file_raises_exception_if_unknown_type(config):
    file_path = config.test_dir / "openapi.unknown"
    with pytest.raises(TypeError):
        Client.from_file(file_path)


def test_endpoint_docstring_constructed_from_spec(spec_dict):
    client = Client(spec_dict)
    assert client.dummy_test_endpoint.__doc__ == (
        "A dummy test endpoint.\n\nA test endpoint that does nothing,"
        " so is pretty dummy, but works fine for testing."
    )


def test_endpoint_docstring_constructed_with_default_values(spec_dict):
    client = Client(spec_dict)
    assert client.dummy_test_endpoint_with_argument.__doc__ == "dummyTestEndpointWithArgument"


def test_common_headers_included_in_request(spec_dict, config, monkeypatch):
    from .application import app

    client = Client(spec_dict, client=TestClient(app), headers={"foo": "bar"})

    def patch_request(request):
        def wrapper(*args, **kwargs):
            client.request_info = {"args": args, "kwargs": kwargs}
            return request(*args, **kwargs)

        return wrapper

    monkeypatch.setattr(client.client, "request", patch_request(client.client.request))
    client.dummy_test_endpoint(headers_={"baz": "bam"})

    headers = dict(client.latest[0].request.headers)
    assert all(item in headers.items() for item in {"foo": "bar", "baz": "bam"}.items())


def test_client_calls_endpoint_with_path_argument(spec_dict, config):
    client = Client(spec_dict, client=TestClient(app))
    response = client.dummy_test_endpoint_with_argument("xyz")
    assert isinstance(response, protocols.Response)
    assert response.data == b'{"foo":"xyz"}'


def test_client_calls_async_endpoint(spec_dict, config):
    client = Client(spec_dict, client=TestClient(app))
    response = client.dummy_test_endpoint_coro()
    assert response.data == b'{"baz":123}'


def test_client_passes_query_parameters(spec_dict, config):
    client = Client(spec_dict, client=TestClient(app))
    client.dummy_test_endpoint(q="hello")
    sent_request = client.latest[0].request
    assert sent_request.url.params["q"] == "hello"


def test_client_sends_form_encoded_body(spec_dict, config):
    client = Client(spec_dict, client=TestClient(app))
    response = client.dummy_form_endpoint(body_={"foo": "bar"})
    assert response.status_code == HTTPStatus.NO_CONTENT


def test_client_accepts_schemapath_spec(spec_dict):
    client = Client(SchemaPath.from_dict(spec_dict))
    assert client.server_url == spec_dict["servers"][0]["url"]


def test_client_loads_spec_from_url_json(spec_dict, monkeypatch):
    class FakeResponse:
        def json(self):
            return spec_dict

        @property
        def text(self):
            return json.dumps(spec_dict)

    monkeypatch.setattr(httpx, "get", lambda url: FakeResponse())
    client = Client.from_url("http://example.com/openapi.json")
    assert client.spec["info"]["title"] == "Test Spec"


def test_client_loads_spec_from_url_yaml(yaml_spec_file, monkeypatch):
    yaml_text = yaml_spec_file.read_text()

    class FakeResponse:
        def json(self):
            raise JSONDecodeError("not json", yaml_text, 0)

        @property
        def text(self):
            return yaml_text

    monkeypatch.setattr(httpx, "get", lambda url: FakeResponse())
    client = Client.from_url("http://example.com/openapi.yaml")
    assert client.spec["info"]["title"] == "Test Spec"
