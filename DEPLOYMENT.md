# OLX Finance Intelligence — Web Deployment

## Streamlit Community Cloud

Deploy from the existing private repository `SherryHuProducts/apexedge-ai-finance-dashboard` using branch `main` and entrypoint `app.py`. `requirements.txt`, `runtime.txt` and `.streamlit/config.toml` define the application environment and warm cream theme.

If a Streamlit Cloud app **already points to this branch**, a GitHub commit should trigger its normal redeployment. Verify the exact app URL in the Streamlit Cloud dashboard before announcing an updated live website. Otherwise create or reconfigure a private app through Streamlit Community Cloud.

Keep the deployment **private/access-controlled**. The OLX app currently uses Streamlit session memory, not enterprise identity segregation or a durable production database. Do not upload sensitive employer records to a public demonstration.

## Web smoke checklist (new OLX app)

- [ ] Main app starts from `app.py` without import errors.
- [ ] Sidebar brand is **OLX**, cream-white background, dark text.
- [ ] Default opening page is **ERP Integration / ERP 集成**, no preloaded sample data.
- [ ] **Financial Reporting / 财务报告** is blank before uploading validated records.
- [ ] **Analysis & Planning / 分析与规划** is blank before upload.
- [ ] Role selector switches **CFO / Sales VP**.
- [ ] Source report upload → **Validate & Load** reveals source/quality results.
- [ ] Financial reporting shows only supplied metrics and selected periods.
- [ ] Analysis shows actual KPI trends and explicitly illustrative pricing assumptions.
- [ ] Missing periods, estimates and unallocated amounts are not fabricated.
- [ ] **Case Studies & Code / 案例与代码** is hidden by default and opens only when toggled.
- [ ] Synthetic case content never appears in the OLX main workspace.
- [ ] **Clear workspace** removes source data and associated GL status.

## What is not deployed

Live retailer/ERP API tokens, EDI providers, scheduler, daily automatic refresh, persistent relational database, production AI analysis, signed-off GAAP reporting and fine-grained tenant access are **not** in this prototype. The ERP Integration page describes their implementation approach, clearly distinguished from functionality currently running.

Optional LLM API keys must never be committed to source control. Production AI and confidential business data require governance approval, access controls, evaluation and audit logging.
