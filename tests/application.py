import json
from http import HTTPStatus

from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route


async def dummy_test_endpoint(request):
    return JSONResponse({"foo": "bar"})


async def dummy_test_endpoint_with_argument(request):
    return JSONResponse({"foo": request.path_params["test_arg"]})


async def dummy_test_endpoint_coro(request):
    return JSONResponse({"baz": 123})


async def dummy_post_endpoint(request):
    body = await request.body()
    assert json.loads(body.decode()) == {"foo": "bar"}
    return Response(status_code=HTTPStatus.NO_CONTENT.value)


app = Starlette(
    routes=[
        Route("/test", dummy_test_endpoint, methods=["GET"]),
        Route("/test", dummy_post_endpoint, methods=["POST"]),
        Route("/test/{test_arg}", dummy_test_endpoint_with_argument, methods=["GET"]),
        Route("/test-async", dummy_test_endpoint_coro, methods=["GET"]),
    ]
)
