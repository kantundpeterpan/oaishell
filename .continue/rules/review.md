---
invokable: true
---

Review this code for potential issues, including:

- **OpenAPI Compliance**: Ensure new engine features correctly handle edge cases in the OpenAPI spec (e.g., missing `operationId`, complex `$ref` paths).
- **Payload Assembly**: Check that `PayloadAssembler` logic correctly handles dot-notation for nested objects and correctly categorizes parameters into path/query/body.
- **TUI Responsiveness**: Verify that changes to `ShellRunner` or the TUI loop don't block input or cause flickering. Ensure `raw_mode` is handled correctly.
- **State Management**: Ensure `ClientState` persistence is atomic and doesn't leak sensitive data into logs.
- **Type Safety**: Check Pydantic models in `config/models.py` for correct default values and type validation.
- **Async/Sync Consistency**: Ensure the engine (which uses `httpx.Client`) is used correctly within the synchronous `prompt_toolkit` loop.

Provide specific, actionable feedback for improvements.
