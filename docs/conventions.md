# Conventions

*   Use trailing slash for endpoints?
*   Use predefined CRUD Terminologies for endpoint methods
*   Do not return SA object instance(s) in endpoint, always return Pydantic schema with only the required information
*   Freeze requirements to `requirements/frozen-{data}` on every release.
*   Use the word `schema` for Pydantic Schema and `model` for SQLAlchemy Model.
*   Use `Schema` class from `core.lib.schemas` for Pydantic Schema.
*   Do not start GET endpoint actions with `get_`.
*   Always add response schemas and possible error responses.
*   Place endpoint actions in order of user flow.

## CRUD Terminologies

*   List
*   Create
*   Retrieve
*   Update
*   Delete
