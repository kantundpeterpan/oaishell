# Features to implement

## Response schemas

Response schemas should also be discovered and shown in the shell / CLI, e.g. in /operations and /operations-tui. Furthermore, based on response schemas, the yaml configuration shoudl make it possible to define the response field that is to be shown in the response panel by default (`default_response_field` or similar). This should cover nested objects and arrays as well (good notation needed). The --debug flag should then trigger a second panel showing the nicely formatted raw response.
The `default_response_field` is to be validated against the Response schema, but an override setting should exist.

