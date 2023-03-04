# PyAPI Client

[![Build Status](https://b11c.semaphoreci.com/badges/pyapi-client/branches/master.svg?style=shields&key=06259646-6937-4157-a127-ff0271ca1501)](https://b11c.semaphoreci.com/projects/pyapi-client)
[![Documentation Status](https://readthedocs.org/projects/pyapi-client/badge/?version=latest)](https://pyapi-client.readthedocs.io/en/latest/?badge=latest)

**PyAPI Client** is a Python library for consuming REST APIs based on [OpenAPI](https://swagger.io/resources/open-api/) specifications.

**WARNING:** This is still a work in progress and not quite ready for production usage. Until version 1.0 is released, any new release can be expected to break backward compatibility.


## Quick Start

```python
from pyapi.client import Client

client = Client.from_file("path/to/openapi.yaml")
result = client.some_endpoint_id("path", "variables", "query_var"="example")
```
