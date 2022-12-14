from pathlib import Path

from pyapi.client import Client

SPEC_PATH = Path(__file__).parent / "petstore.yaml"

client = Client.from_file(SPEC_PATH)

assert client.find_pets_by_status(status="available").payload == {
    "pets": [{"name": "Athena", "photoUrls": ["sdfsdfasdf", "asdasdasdasd"]}]
}
