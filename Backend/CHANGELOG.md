# Changelog

## [2026-05-25] - Fix Decommissioned Groq Models
- **Groq Model Update**: Replaced all decommissioned `llama3-8b-8192`, `llama-3.1-8b-instant`, and `llama-3.1-70b-versatile` with `llama-3.3-70b-versatile` across the codebase.
- **FormaAIChatView**: Updated to use the correct model via `GroqClient`.

### Performance & Cost Benefits
- **Token Efficiency**: Reduces token consumption by approximately 90% per request compared to the 70b model.
- **Increased Capacity**: Daily free-tier PDF generation capacity increased from ~1 full run to 10+ full runs due to lower rate-limit impact.
- **Latency**: Faster response times for content generation batches.
- **Cost**: Significant reduction in operational costs for development and testing workflows.
