# Validation plan and evidence

## Unit and integration coverage

- Gross-to-net and gross-profit calculations
- Inventory snapshot separation and missing values
- Cross-source metric collision prevention
- Independent GL control totals
- Exact gross-profit bridge with new SKUs
- CFO/Sales metric parity
- Promotion and action queue guardrails
- AI aggregate evidence packet privacy
- Decision-state validation and audit events
- Streamlit AppTest CFO, Sales and Decision routes

## Local test

```bash
python -m pip install -r requirements.txt pytest
python -m pytest -q
```

Run `python -m pytest -q` after any source modification. Never claim GitHub Actions passed until the repository Actions page shows a successful run.

## Known limits

No live API call is part of CI. API keys and authentic employer data are intentionally excluded from tests. Full deployment and browser-specific accessibility tests require a deployed app and suitable credentials.
