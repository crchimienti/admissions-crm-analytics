"""Canonical CRM schema crm-canonical/0.1.1 (F2): contract, validation, CSV mapping, history, KPI availability.

Esquema CRM canónico crm-canonical/0.1.1 (F2): contrato, validación, mapeo CSV, historial y disponibilidad de KPIs.

Flow: profile CSV -> mapping.py -> canonical tables (validated by validate.py) -> adapters/<profile>.py -> the
profile's metric code (for admissions: src/metrics.py, F1 code plus the authorised v1.2.1-f2 robustness fix).
Only the admissions profile exists; nothing here is claimed to work for other funnels or CRMs.
No network, no CRM connection, synthetic data only.
"""
