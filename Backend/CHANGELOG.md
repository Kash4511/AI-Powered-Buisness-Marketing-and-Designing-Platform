# Changelog

## [2026-03-06] - Cost Optimization Switch to llama-3.1-8b-instant

### Changed
- **Groq Model Update**: Replaced `llama-3.3-70b-versatile` with `llama-3.1-8b-instant` in `groq_client.py`.

### Performance & Cost Benefits
- **Token Efficiency**: Reduces token consumption by approximately 90% per request compared to the 70b model.
- **Increased Capacity**: Daily free-tier PDF generation capacity increased from ~1 full run to 10+ full runs due to lower rate-limit impact.
- **Latency**: Faster response times for content generation batches.
- **Cost**: Significant reduction in operational costs for development and testing workflows.
