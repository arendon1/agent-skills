# ClickUp Error Handling

## HTTP Status Codes

| Code | Meaning | Retry? | Action |
|------|---------|--------|--------|
| 200 | Success | — | Continue |
| 201 | Created | — | Resource created successfully |
| 204 | No Content | — | Deletion or clear operation succeeded |
| 400 | Bad Request | No | Fix the request payload or parameters |
| 401 | Unauthorized | No | API key invalid or expired — check at https://app.clickup.com/settings |
| 403 | Forbidden | No | API key lacks permissions for this resource |
| 404 | Not Found | No | Verify the resource ID exists |
| 409 | Conflict | No | Duplicate resource or state conflict |
| 429 | Rate Limited | Yes | **Exponential backoff:** 1s → 2s → 4s |
| 500 | Internal Server Error | Yes | **Retry up to 3x** with backoff |
| 502 | Bad Gateway | Yes | Temporary — retry |
| 503 | Service Unavailable | Yes | Temporary — retry |

## Rate Limiting

ClickUp enforces rate limits per API key. Exact limits are not publicly documented but typically:

- **~100 requests per minute** for most endpoints
- Bulk operations (e.g., creating many tasks) should include delays

## Retry Strategy

The client in `scripts/client.py` implements automatic retries:

```python
MAX_RETRIES = 3

# Exponential backoff
for attempt in range(MAX_RETRIES):
    try:
        response = client.request(...)
        if response.status_code < 500:
            return response
    except RequestException:
        if attempt == MAX_RETRIES - 1:
            raise
        time.sleep(2 ** attempt)  # 1s, 2s, 4s
```

**Behavior:**
- 4xx errors: Return immediately (client error — retrying won't help)
- 5xx errors: Retry with exponential backoff
- Network errors: Retry with exponential backoff

## Error Response Format

Error responses include a JSON body:

```json
{
  "err": "Error message",
  "ECODE": "ERROR_CODE"
}
```
