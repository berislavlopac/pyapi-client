# PyAPI Client

Python client library for making requests to any OpenAPI-based service.

[![Build Status](https://b11c.semaphoreci.com/badges/pyapi-client/branches/master.svg?style=shields&key=06259646-6937-4157-a127-ff0271ca1501)](https://b11c.semaphoreci.com/projects/pyapi-client)
[![Documentation Status](https://readthedocs.org/projects/pyapi-client/badge/?version=latest)](https://pyapi-client.readthedocs.io/en/latest/?badge=latest)

Using an API's [OpenAPI](https://www.openapis.org/) spec as a starting point, PyAPI Client a user to call any operation as if it was a Python method.

**WARNING:** This is still very much work in progress and not quite ready for production usage. Until version 1.0 is released, any version can be expected to break backward compatibility.

Basic Usage
-----------

PyAPI Client is a class that takes a dictionary or a `Spec` object; there is also a helper class method that will load the spec from a provided file:

```python
from pyapi.client import Client
client = Client.from_file("path/to/openapi.yaml")
```
    
On instantiation, the client adds a number of methods to itself, each using a snake-case version of an `operationId` as a name. To make a request to the API, call the corresponding method; e.g. if the spec contains an `operationId` named `someEndpointId`, it can be called as:
 
```python
result = client.some_endpoint_id("foo", "bar", query_var="example")
```

If the corresponding API endpoint accepts any path variables (e.g. `/root/{id}/{name}`), they can be passed in the form of positional arguments to the method call. Similarly, any query or body parameters can be passed as keyword arguments.

Before a request is sent, it is validated using the OpenAPI spec; the same happens to a response upon receiving. Any errors are raised as exceptions.

Advanced Usage
--------------

The `Client` class accepts a few optional, keyword-only arguments on instantiation:

* `server_url`: A server hostname that will be used to make the actual requests. If it is not present in the `servers` list of the specification it will be appended, and if none is specified the first from the `servers` list will be used. 
* `client`: The HTTP client implementation used to make actual requests. The  [`httpx`](https://www.encode.io/httpx/) library is used by default, but it can be replaced by any object compatible with the `Requests` client.
* `request_class` and `response_class`: The classes used to wrap the incoming request and response, respectively, for validation. By default, it is the built-in `OpenAPIRequest` and `OpenAPIResponse`; they can be subclassed and modified if additional functionality is required.
