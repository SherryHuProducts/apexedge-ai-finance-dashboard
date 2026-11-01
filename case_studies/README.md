# Case Studies & Code / 案例与代码

This folder isolates the **legacy synthetic dashboard entrypoint** and the **demonstration-only fixture catalog** from the primary OLX workspace.

- [Archived legacy UI entrypoint](legacy_dashboard_app.py)
- [Mock broken Amazon input](fixtures/broken_amazon.csv)
- [Mock missing-cost input](fixtures/missing_cost.csv)
- [Mock settlement mismatch](fixtures/settlement_mismatch.csv)

In the current `app.py`, case-study pages are accessible **only after enabling the separate `Case Studies & Code / 案例与代码` toggle**. By default the OLX workspace is blank and does not generate or load any synthetic data.

**Compatibility note:** Existing standalone Python demo modules (`thin_slice.py`, `multi_channel_connectors.py`, `master_data_mapping.py`, `channel_pl.py`, `finance_data.py`) remain at repository root because old tests and portfolio pages import them directly. Their data is not loaded into the OLX default financial workspace. The archived UI is reference-only; the case toggle uses existing individual demos.

These examples are synthetic. They are **not** OLX business data, production API integrations, or month-end financial statements.
