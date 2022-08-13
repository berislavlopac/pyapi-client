# PyAPI Client

**PyAPI Client** is a Python library for consuming REST APIs based on [OpenAPI](https://swagger.io/resources/open-api/) specifications.

**WARNING:** This is still a work in progress and not quite ready for production usage. Until version 1.0 is released, any new release can be expected to break backward compatibility.


## Quick Start

```python
from pyapi.client import Client

client = Client.from_file("path/to/openapi.yaml")
result = client.some_endpoint_id("path", "variables", "query_var"="example")
```
