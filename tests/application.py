import json
from http import HTTPStatus
from pathlib import Path

from pyapi.server import Application
from starlette.responses import Response

file_path = Path(__file__).parent / "openapi.json"
with file_path.open() as spec_file:
    spec_dict = json.load(spec_file)

app = Application(spec_dict)


@app.endpoint
def dummy_test_endpoint(request):
    return {"foo": "bar"}


@app.endpoint
def dummy_test_endpoint_with_argument(request):
    return {"foo": request.path_params["test_arg"]}


@app.endpoint
async def dummy_test_endpoint_coro(request):
    return {"baz": 123}


@app.endpoint
async def dummy_post_endpoint(request):
    body = await request.body()
    assert json.loads(body.decode()) == {"foo": "bar"}
    return Response(status_code=HTTPStatus.NO_CONTENT.value)


async def endpoint_returning_nothing(request): ...
