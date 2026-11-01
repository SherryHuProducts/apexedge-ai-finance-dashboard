# ApexEdge deployment guide

## Demo policy

Use **synthetic data only** in a public demo. The GitHub repository is currently private. Do not change its visibility without the owner's approval. No API key is necessary to demonstrate deterministic CFO/Sales metrics and human decision review.

## Streamlit Community Cloud

1. Sign into Streamlit Community Cloud with an authorized GitHub account.
2. Select **Create app → From GitHub**, then authorize access to the `SherryHuProducts/apexedge-ai-finance-dashboard` repository.
3. Set branch `main` and entrypoint `app.py`.
4. Use `requirements.txt` and `runtime.txt` from this repo.
5. Keep the app private or access-controlled while testing. Review its sharing policy before publishing.
6. Run the smoke checklist below.
7. To enable optional OpenAI explanations, configure `OPENAI_API_KEY` and `OPENAI_MODEL` as platform secrets or environment variables. The current app reads environment variables. Never put API keys into Git.
8. Public deployment with optional AI should include usage controls and a budget limit before inviting unknown users.

## Smoke checklist

- [ ] CFO default landing page renders without errors
- [ ] Sales mode shows four channels and SKU table
- [ ] Promotion break-even reacts to additional-discount slider
- [ ] Both audiences use consistent Net Revenue / Contribution Profit
- [ ] Decision Intelligence displays anomalies with evidence
- [ ] No API key: deterministic signals still function
- [ ] Optional AI requires consent and sends only the previewed aggregated packet
- [ ] Data Quality shows **NOT SUPPLIED** before GL upload
- [ ] No uploaded file data is committed or sent outside authorized systems
- [ ] Exported decision events are clearly session-only

## Security / production gaps

The Streamlit prototype is **not** a production financial system: it has no identity-based authorization, durable audit store, separate tenants, API rate limiting or enterprise secrets governance. Do not use it to process confidential employer records in a publicly accessible deployment.
