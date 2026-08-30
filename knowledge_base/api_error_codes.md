# API error code reference

- 401 Unauthorized: the API key is missing or invalid. Check the key is
  being sent in the Authorization header and hasn't been revoked.
- 403 Forbidden: the API key is valid but doesn't have permission for this
  action. Check the key's assigned scopes/permissions.
- 429 Too Many Requests: the rate limit was exceeded. Wait and retry with
  backoff; repeated 429s usually mean requests need to be batched.
- 500 Internal Server Error: an unexpected failure on the server. If this
  persists across retries, it should be reported with the request ID from
  the response headers.
