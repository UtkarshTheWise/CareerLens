from app.schemas.api import Error

# Declared on every router so the generated OpenAPI carries the contract's Error shape.
ERROR_RESPONSES: dict[int | str, dict] = {
    404: {"model": Error, "description": "Not found"},
    422: {"model": Error, "description": "Invalid input"},
}
