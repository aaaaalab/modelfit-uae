# Live source-linked evidence summaries

Create an OpenAI project API key at https://platform.openai.com/api-keys . Select the intended project, create a secret key, and copy it directly into Railway. Ensure the project has API billing/credits and access to the configured model. Never paste a key in chat, source code or a frontend variable.

Railway project: ModelFit UAE Hackathon 2026 → production → ModelFit application service (not MySQL) → Variables:

- `OPENAI_API_KEY`: your secret key. Enter only in Railway; use a sealed variable if offered.
- `OPENAI_MODEL`: `gpt-4.1-mini` (optional; this is the default).

Save and apply/deploy the variable changes. In the app refresh → Evaluations → Evidence library → open an evidence record → Draft AI summary. Only a successful provider response displays `Live AI · OpenAI · <model>`, with record references and a human-review warning. A configured key is not proof of a successful connection. Missing key uses the explicitly simulated assistant. An invalid key, quota error or invalid output shows an error, never a fake live summary.

Only selected public/synthetic evidence fields are sent to https://api.openai.com/v1/responses. No external URLs are fetched, no tools are granted, and no findings/approvals are saved by the assistant. `store=false` is sent; this is not a claim of zero data retention. Output is untrusted AI text and still requires human review. Provider/model access and billing depend on the user's OpenAI project.

Limits: 600 output tokens per request, 25-second timeout, 20 requests per hour across the single application process, 10-minute cache keyed by evidence content and model, maximum 100 cached summaries. Limits reset on restart and are prototype cost controls, not a distributed abuse prevention system. Model evaluation outputs remain simulated even if evidence summarization is live.

Verification completed without credentials: 21 local tests passed, including mocked provider success, cache behavior, source-ID enforcement and sanitized provider errors; TypeScript and production build passed. No real provider call has been verified yet.
