"""Declarative KPI specification kpi-spec/0.1 (F3.0, v1.3.0-f3).

Especificación declarativa de KPIs kpi-spec/0.1 (F3.0).

A small, closed configuration (schema/kpi_spec_v0.1.yaml) evaluated on canonical datasets: five operations
(count, share, ratio, duration_stat, field_stat), a closed list of AND-only filters, named populations and declared
fields. No expressions, no OR, no embedded code. It runs in parallel with src/metrics.py, which remains the official
reference in F3, and never imports it. Admissions profile only; no portability claim; synthetic data only.
"""
