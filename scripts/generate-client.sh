#! /usr/bin/env bash

set -e
set -x

# Generate OpenAPI JSON file
python -c "import app.main; import json; print(json.dumps(app.main.app.openapi()))" > ./openapi.json

# Generate client
npx @hey-api/openapi-ts