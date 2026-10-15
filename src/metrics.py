"""Metric computation for the admissions profile (F1).

Cálculo de métricas del perfil de admisiones (F1).

This module is the single implementation of every table and KPI shown in the analysis notebook and of the
47 baseline metrics. The notebook only calls these functions and formats / plots what they return.
It was extracted from the F0 notebook code (`scripts/build_notebook.py`, v1.0.0-f0) without changing any
expression, so its results must equal `baseline/metrics_v1.json` (see tests/test_regression_f0.py).

Scope: the admissions profile only. Nothing here is claimed to apply to other funnels or CRMs.

Rules: pure functions over a `Context`; no printing, no plotting, no randomness, no network, and no file
writes. The only I/O is `load_context`, which reads the CSV files and the configuration.

Dependencies: numpy, pandas, pyyaml and src/checks.py (unchanged since F0).

v1.2.1-f2 (authorised robustness fix, no definition or value change): every ratio goes through `rate()`, so a zero
denominator gives NaN (reported as undefined) instead of ZeroDivisionError or inf; `Context.bot_pre` looks up the
first-appointment slot with reindex (datetime kept) when there are no appointments; `Context.personal_wa_appointments` builds a typed
boolean column when no appointment is scheduled from 2025-07-01; `Context.showlead` is typed bool when it is empty. On the generated data all 47 values are unchanged.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

try:
    import checks
except ImportError:  # pragma: no cover
    from src import checks

ROOT = Path(__file__).resolve().parents[1]
KPI_EN, KPI_ES = "docs/kpi_definitions.md", "docs/kpi_definitions.es.md"
INPUT_FILES = ["config/simulation_params.yaml", "data/leads.csv", "data/activities.csv", "data/dq_ground_truth.csv"]
SYNTHETIC_NOTE = "All values are synthetic (seed 42). Not historical data, not findings about any real organisation."


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #
def rate(num, den):
    """num / den, NaN when the denominator is 0 (an undefined rate, never a zero rate)."""
    return np.nan if den == 0 else num / den


def wilson_interval(k, n, z=1.96):
    """95 % Wilson score interval for k successes out of n (NaN, NaN when n = 0)."""
    if n == 0:
        return (np.nan, np.nan)
    p = k / n; d = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return (c - h, c + h)


def sha256_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# Context: populations computed once
# --------------------------------------------------------------------------- #
class Context:
    """Populations shared by all metrics. Inputs are copied, never modified.

    leads: all rows of leads.csv (+ `cohort`) · E: eligible leads (+ `mature`) · EM: mature eligible (+ `has_held`)
    RX: reactivations · M: eligible manual · Mw: manual SLA window (+ `resp_h`, `weekend_arrival`)
    I: all interview rows · IE: eligible appointments · show: eligible held/no_show appointments
    """

    def __init__(self, leads: pd.DataFrame, acts: pd.DataFrame, gt: pd.DataFrame, cfg: dict,
                 maturity_days: int = 60, root: Path | None = None):
        self.raw_leads = leads.copy()
        self.A = acts.copy()
        self.G = gt.copy()
        self.cfg = cfg
        self.root = Path(root) if root is not None else None
        self.maturity_days = maturity_days
        self.SNAP = self.raw_leads.snapshot_date.iloc[0]
        self.MATURITY = pd.Timedelta(days=maturity_days)

        L = self.raw_leads.copy()
        L["cohort"] = L.created_at.dt.to_period("M")
        self.L = L
        E = L[~L.is_duplicate & ~L.is_reactivation].copy()
        E["mature"] = (self.SNAP - E.created_at) >= self.MATURITY
        self.E = E
        self.RX = L[L.is_reactivation].copy()

        M = E[E.entry_path == "manual"].copy()
        Mw = M[M.created_at <= self.SNAP - pd.Timedelta(hours=24)].copy()
        Mw["resp_h"] = (Mw.first_human_attempt_at - Mw.created_at).dt.total_seconds() / 3600
        Mw["weekend_arrival"] = Mw.created_at.dt.weekday >= 5
        self.M, self.Mw = M, Mw

        EM = E[E.mature].copy()
        EM["has_held"] = EM.entered_interview_held_at.notna()
        self.EM = EM

        A = self.A
        self.I = A[A.activity_type == "interview"]
        I = self.I
        IE = I[I.lead_id.isin(E.lead_id) & I.replaced_by_activity_id.isna() & (I.interview_scheduled_for <= self.SNAP)].copy()
        IE = IE.merge(E[["lead_id", "entry_path", "cohort", "mature"]], on="lead_id")
        IE["month"] = IE.interview_scheduled_for.dt.to_period("M")
        self.IE = IE
        self.show = IE[IE.interview_outcome.isin(["held", "no_show"])]

        self.OP = E[~E.pipeline_stage.isin(["closed_won", "closed_lost"])]
        self.W = E[E.enrolled_at.notna()]   # period view: all enrollments recorded by the snapshot

    # ----- derived populations used by several metrics ----- #
    @cached_property
    def showlead(self) -> pd.Series:
        show = self.show
        # v1.2.1-f2: explicit bool dtype; with no appointment the empty result was a string series and .mean() raised
        return show[show.mature].groupby("lead_id").interview_outcome.apply(lambda s: (s == "held").any()).astype(bool)

    @cached_property
    def personal_wa_appointments(self) -> pd.DataFrame:
        A = self.A
        pw = A[(A.sequence_step == "personal_whatsapp")][["lead_id", "activity_at"]]
        s2 = self.show[self.show.interview_scheduled_for >= "2025-07-01"].copy()
        # v1.2.1-f2: typed boolean column, so an empty selection stays a boolean mask (it was an empty object list)
        s2["personal_wa"] = pd.Series([bool(((pw.lead_id == l) & (pw.activity_at < t)).any())
                                       for l, t in zip(s2.lead_id, s2.interview_scheduled_for)], index=s2.index, dtype=bool)
        return s2

    @cached_property
    def bot_pre(self) -> dict:
        A, I, E = self.A, self.I, self.E
        first_appt = I.sort_values("activity_at").groupby("lead_id").interview_scheduled_for.first()
        # v1.2.1-f2: look the slot up with reindex, which keeps the datetime dtype when there is no appointment row
        # (Series.map with an empty datetime mapper casts it to float and raises TypeError)
        B = E[E.entry_path == "bot_booked"][["lead_id"]].assign(
            first_appt=lambda d: pd.Series(first_appt.reindex(d.lead_id).to_numpy(), index=d.index))
        pre = A.merge(B, on="lead_id")
        pre = pre[pre.activity_at < pre.first_appt]
        conf = pre[(pre.sequence_name == "pre_interview_reminder") & (pre.actor_type == "bot")].lead_id.unique()
        human = pre[(pre.actor_type == "advisor") & ~pre.is_automated.astype(bool)].lead_id.unique()
        return {"B": B, "conf": conf, "human": human}

    @cached_property
    def lost(self) -> pd.DataFrame:
        E = self.E
        LO = E[E.pipeline_stage == "closed_lost"].copy()
        LO["exit_point"] = np.select([LO.entered_enrollment_link_sent_at.notna(), LO.entered_form_completed_at.notna(),
                                      LO.entered_interview_held_at.notna(), LO.entered_interview_booked_at.notna()],
                                     ["after link", "after form", "after interview held", "after booking"], "before booking")
        LO["reason"] = LO.lost_reason.fillna("(missing — DQ anomaly)")
        return LO

    @cached_property
    def nurture(self) -> dict:
        E, A = self.E, self.A
        NU = E[E.nurture_started_at.notna()]
        full = NU[NU.nurture_started_at <= self.SNAP - pd.Timedelta(days=150)]
        nr = A[A.sequence_name == "nurture"]
        return {"NU": NU, "full": full, "nr": nr}

    @cached_property
    def overdue_leads(self) -> set:
        A = self.A
        return set(A[(A.activity_type == "task") & (A.task_status == "overdue")].lead_id)

    @cached_property
    def followup(self) -> dict:
        return checks.followup_within_48h(self.raw_leads, self.A, hours=48)

    @cached_property
    def workload_frames(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        E, cfg = self.E, self.cfg
        wts = cfg["team"]["assignment_weight"]
        work = E.pivot_table(index="first_owner_id", columns="cohort", values="lead_id", aggfunc="size", fill_value=0)
        expected = pd.DataFrame({p: {a: cfg["volume"]["monthly_new_eligible"][p.month] * w for a, w in wts.items()}
                                 for p in work.columns})
        return work, expected

    @cached_property
    def cohorts(self) -> pd.DataFrame:
        return checks.cohort_maturity(self.raw_leads, maturity_days=self.maturity_days)

    @cached_property
    def check_results(self) -> tuple[pd.DataFrame, list]:
        ch = checks.Checker(self.raw_leads, self.A, self.G)
        return ch.run(), ch.warnings


def build_context(leads, acts, gt, cfg, maturity_days=60, root=None) -> Context:
    """Build a Context from in-memory data (no I/O)."""
    return Context(leads, acts, gt, cfg, maturity_days=maturity_days, root=root)


def load_context(data_dir=ROOT / "data", config_path=ROOT / "config" / "simulation_params.yaml",
                 maturity_days=60) -> Context:
    """Read the CSV files (with the same parsing as src/checks.py) and the configuration."""
    leads, acts, gt = checks.load(Path(data_dir))
    cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    return Context(leads, acts, gt, cfg, maturity_days=maturity_days, root=Path(data_dir).parent)


# --------------------------------------------------------------------------- #
# Section functions (return numbers; formatting stays in the notebook)
# --------------------------------------------------------------------------- #
def validation_summary(ctx: Context) -> dict:
    results, warnings = ctx.check_results
    logic = results[results.category == "logic"]
    anomalies = results[results.category == "anomaly"][["check", "injected", "detectable", "detected",
                                                         "not_detectable", "detail", "note"]].reset_index(drop=True)
    return {"logic_checks": len(logic), "logic_checks_with_violations": int((logic.violations > 0).sum()),
            "logic_violations": int(logic.violations.sum()), "anomalies": anomalies,
            "governance_indicator": results[results.category == "governance"].iloc[0], "warnings": list(warnings)}


def cohort_table(ctx: Context) -> pd.DataFrame:
    """Per-lead maturity and computed cohort label, plus duplicates and reactivations per month."""
    L, RX = ctx.L, ctx.RX
    coh = ctx.cohorts.copy()
    coh["duplicates"] = L[L.is_duplicate].groupby("cohort").size().reindex(coh.index, fill_value=0)
    coh["reactivations"] = RX.groupby("cohort").size().reindex(coh.index, fill_value=0)
    return coh


def population_counts(ctx: Context) -> dict:
    return {"eligible_leads": len(ctx.E), "mature_eligible_leads": len(ctx.EM), "duplicates": int(ctx.L.is_duplicate.sum()),
            "reactivations": len(ctx.RX), "maturity_threshold": ctx.SNAP - ctx.MATURITY, "snapshot": ctx.SNAP}


def sla_summary(ctx: Context) -> pd.Series:
    E, M, Mw = ctx.E, ctx.M, ctx.Mw
    open_ = ~E.pipeline_stage.isin(["closed_won", "closed_lost"])
    att = M.first_human_attempt_at.notna()
    return pd.Series({
        "eligible leads": len(E),
        "share manual route": rate(len(M), len(E)),
        "share bot route": rate((E.entry_path == "bot_booked").sum(), len(E)),
        "manual: contacted (≥1 human attempt)": rate(att.sum(), len(M)),
        "manual: untouched at snapshot (open, no attempt) / open manual": rate((open_[M.index] & ~att).sum(), open_[M.index].sum()),
        "manual: first attempt ≤ 24 h": rate((Mw.resp_h <= 24).sum(), len(Mw)),
        "manual: first attempt same calendar day": rate((Mw.first_human_attempt_at.dt.date == Mw.created_at.dt.date).sum(), len(Mw)),
        "manual: median first response (h)": Mw.resp_h.median(),
        "manual: p90 first response (h)": Mw.resp_h.quantile(0.9),
        "contact rate (connected / with attempt)": rate(E.first_connected_at[E.first_human_attempt_at.notna()].notna().sum(), E.first_human_attempt_at.notna().sum()),
        "reassignment rate (manual)": rate(M.reassigned_flag.sum(), len(M)),
    })


def sla_by_arrival(ctx: Context) -> pd.DataFrame:
    Mw = ctx.Mw
    return Mw.groupby(np.where(Mw.weekend_arrival, "weekend arrival", "weekday arrival")).agg(
        leads=("lead_id", "size"), sla_24h=("resp_h", lambda s: (s <= 24).mean()), median_h=("resp_h", "median"))


def bot_pre_interview(ctx: Context) -> dict:
    b = ctx.bot_pre
    n = len(b["B"])
    return {"bot_route_leads": n, "confirmation_leads": len(b["conf"]), "human_contact_leads": len(b["human"]),
            "confirmation_rate": rate(len(b["conf"]), n), "human_contact_rate": rate(len(b["human"]), n)}


def main_kpi_by_cohort(ctx: Context, mature_only: bool = False) -> pd.DataFrame:
    """Main KPI per cohort; partial cohorts carry their label and mature share and must not be compared."""
    EM, coh = ctx.EM, ctx.cohorts
    kpi = EM.groupby("cohort").agg(leads=("lead_id", "size"), held=("has_held", "sum"))
    for route, col in (("manual", "manual_route"), ("bot_booked", "bot_route")):
        kpi[col] = EM[EM.entry_path == route].groupby("cohort").has_held.mean()
    kpi["main_kpi"] = kpi.held / kpi.leads
    kpi["cohort_label"] = coh.label.reindex(kpi.index)
    kpi["mature_share"] = coh.mature_share.reindex(kpi.index)
    kpi = kpi[["cohort_label", "mature_share", "leads", "held", "main_kpi", "manual_route", "bot_route"]]
    return kpi[kpi.cohort_label == "mature"] if mature_only else kpi


def main_kpi_totals(ctx: Context) -> pd.Series:
    EM = ctx.EM
    return pd.Series({"mature eligible leads": len(EM),
                      "MAIN KPI interviews held / opportunities": EM.has_held.mean(),
                      "  manual route": EM.loc[EM.entry_path == "manual", "has_held"].mean(),
                      "  bot route": EM.loc[EM.entry_path == "bot_booked", "has_held"].mean(),
                      "booking rate (≥1 appointment)": EM.entered_interview_booked_at.notna().mean()})


def appointment_metrics(ctx: Context) -> dict:
    I, IE, show = ctx.I, ctx.IE, ctx.show
    rates = pd.Series({
        "per-appointment show rate (all)": (show.interview_outcome == "held").mean(),
        "  manual route": (show[show.entry_path == "manual"].interview_outcome == "held").mean(),
        "  bot route": (show[show.entry_path == "bot_booked"].interview_outcome == "held").mean(),
        "cancellation rate": (IE.interview_outcome == "cancelled").mean(),
    })
    rates["per-lead show rate (mature cohorts)"] = ctx.showlead.mean()
    return {"rates": rates,
            "excluded": {"rescheduled_replaced": int((I.interview_outcome == "rescheduled").sum()),
                         "pending_future": int((I.interview_outcome == "pending").sum()),
                         "cancelled_eligible": int((IE.interview_outcome == "cancelled").sum())},
            "appointments_held_or_no_show": len(show), "per_lead_denominator": len(ctx.showlead)}


def show_rate_by_month(ctx: Context) -> pd.Series:
    show = ctx.show
    return show.groupby("month").interview_outcome.apply(lambda s: (s == "held").mean())


def personal_whatsapp_association(ctx: Context) -> pd.DataFrame:
    """Association only: the generator programs zero effect of the personal WhatsApp on attendance."""
    s2 = ctx.personal_wa_appointments
    assoc = s2.groupby("personal_wa").agg(appointments=("activity_id", "size"),
                                          show_rate=("interview_outcome", lambda s: (s == "held").mean()))
    assoc[["ci_low", "ci_high"]] = [wilson_interval(round(r.show_rate * r.appointments), r.appointments)
                                    for r in assoc.itertuples()]
    return assoc


def bot_route_half_comparison(leads: pd.DataFrame) -> dict:
    """Bot-route held-interview rate, Jan–Jun vs Jul–Oct cohorts, with a two-proportion z statistic."""
    d = leads[~leads.is_duplicate & ~leads.is_reactivation & (leads.entry_path == "bot_booked")
              & (pd.to_datetime(leads.created_at) <= "2025-10-31 23:59:59")].copy()
    d["half"] = np.where(pd.to_datetime(d.created_at).dt.month >= 7, "Jul–Oct", "Jan–Jun")
    g = d.groupby("half").entered_interview_held_at.agg(n="size", held=lambda s: s.notna().mean())
    p = d.entered_interview_held_at.notna().mean()
    z = (g.held["Jul–Oct"] - g.held["Jan–Jun"]) / np.sqrt(p * (1 - p) * (1 / g.n["Jan–Jun"] + 1 / g.n["Jul–Oct"]))
    return {"Jan–Jun": g.held["Jan–Jun"], "Jul–Oct": g.held["Jul–Oct"], "z": z}


def funnel(ctx: Context) -> pd.DataFrame:
    EM = ctx.EM
    steps = [("eligible leads", EM.lead_id.notna()), ("interview booked", EM.entered_interview_booked_at.notna()),
             ("interview held", EM.entered_interview_held_at.notna()), ("form completed", EM.entered_form_completed_at.notna()),
             ("enrollment link sent", EM.entered_enrollment_link_sent_at.notna()), ("enrolled", EM.enrolled_at.notna())]
    fun = pd.DataFrame({"leads": [m.sum() for _, m in steps]}, index=[s for s, _ in steps])
    fun["% of eligible"] = fun.leads / fun.leads.iloc[0]
    fun["% of previous"] = fun.leads / fun.leads.shift(1)
    return fun


def directional_rates(ctx: Context) -> pd.Series:
    EM = ctx.EM
    held = EM.entered_interview_held_at.notna()
    return pd.Series({"forms completed / interviews held": rate(EM.entered_form_completed_at.notna().sum(), held.sum()),
                      "enrollments / interviews held": rate(EM.enrolled_at.notna().sum(), held.sum()),
                      "links / forms": rate(EM.entered_enrollment_link_sent_at.notna().sum(), EM.entered_form_completed_at.notna().sum()),
                      "enrollments / eligible leads": EM.enrolled_at.notna().mean()})


def _cycle_days(ctx: Context) -> pd.Series:
    EM = ctx.EM
    return (EM.enrolled_at - EM.created_at).dt.total_seconds().div(86400).dropna()


def sales_cycle(ctx: Context) -> dict:
    cyc = _cycle_days(ctx)
    return {"median_days": cyc.median(), "mean_days": cyc.mean(), "n": len(cyc)}


def segment_table(ctx: Context, by: str) -> pd.DataFrame:
    """Mature cohorts by segment. Differences reproduce the scenario's channel and profile modifiers."""
    g = ctx.EM.groupby(by)
    out = pd.DataFrame({
        "leads": g.size(),
        "held / leads": g.entered_interview_held_at.apply(lambda s: s.notna().mean()),
        "enrolled / leads": g.enrolled_at.apply(lambda s: s.notna().mean()),
        "enrolled / held": g.apply(lambda d: rate(d.enrolled_at.notna().sum(), d.entered_interview_held_at.notna().sum()), include_groups=False),
        "ILOC share": g.lost_reason.apply(lambda s: (s == "iloc").mean()),
        "net € per lead": g.net_price.apply(lambda s: s.fillna(0).mean()),
    })
    return out.sort_values("leads", ascending=False)


BAND_LABELS = ["<100", "100-120 usual", "121-150 high", ">150 alert"]


def workload(ctx: Context) -> dict:
    """Eligible leads by first owner and month (scenario assignment weight; not a performance signal)."""
    work, expected = ctx.workload_frames
    bands = pd.cut(work.stack(), [-1, 99, 120, 150, 10**6], labels=BAND_LABELS)
    return {"realised": work, "expected": expected,
            "bands": bands.value_counts().reindex(BAND_LABELS).to_dict(),
            "over_150_realised": int((work > 150).sum().sum()), "over_150_expected": int((expected > 150).sum().sum()),
            "reactivations_by_first_owner": ctx.RX.groupby("first_owner_id").size().to_dict()}


def advisor_table(ctx: Context, owner_col: str) -> pd.DataFrame:
    """Exploratory: all advisors share the same scenario parameters."""
    rows = []
    for a, d in ctx.EM.groupby(owner_col):
        n = len(d); k = d.entered_interview_held_at.notna().sum()
        lo, hi = wilson_interval(k, n)
        m = d[d.entry_path == "manual"]
        mw = m[m.first_human_attempt_at.notna()]
        rows.append({"advisor": a, "n leads": n, "held / leads": k / n, "95% CI low": lo, "95% CI high": hi,
                     "enrolled / leads": d.enrolled_at.notna().mean(),
                     "manual SLA ≤24h": ((mw.first_human_attempt_at - mw.created_at) <= pd.Timedelta(hours=24)).sum() / max(len(m), 1)})
    return pd.DataFrame(rows).set_index("advisor")


def advisor_activity_counts(ctx: Context) -> dict:
    A = ctx.A
    return A[A.actor_type == "advisor"].groupby("actor_id").size().to_dict()


def lost_reasons(ctx: Context) -> dict:
    LO = ctx.lost
    return {"by_exit_point": pd.crosstab(LO.exit_point, LO.reason, margins=True),
            "distribution": LO.lost_reason.value_counts(normalize=True)}


def nurture_summary(ctx: Context) -> dict:
    n, RX = ctx.nurture, ctx.RX
    full, nr = n["full"], n["nr"]
    return {"entered_nurture": len(n["NU"]), "complete_window": len(full),
            "reactivation_rate_complete_window": rate((full.nurture_end_reason == "reactivated").sum(), len(full)),
            "reactivated_leads": len(RX), "reactivated_enrolled": int(RX.enrolled_at.notna().sum()),
            "nurture_emails": len(nr),
            "email_failure_rate": rate(nr.email_status.isin(["not_sent", "failed"]).sum(), len(nr))}


def governance(ctx: Context) -> dict:
    E, L, OP, G, A = ctx.E, ctx.L, ctx.OP, ctx.G, ctx.A
    ov, FU = ctx.overdue_leads, ctx.followup
    indicators = pd.Series({
        "open leads at snapshot": len(OP),
        "open without next task": rate((~OP.has_open_task.astype(bool)).sum(), len(OP)),
        "open with overdue task": rate(OP.lead_id.isin(ov).sum(), len(OP)),
        "follow-up 48 h — denominator (eligible, window complete)": FU["denominator"],
        "follow-up 48 h — numerator (≥1 manual call/WhatsApp in window)": FU["numerator"],
        "held with manual advisor follow-up within 48 calendar hours": FU["rate"],
        "closed-lost without reason": rate((E.pipeline_stage.eq("closed_lost") & E.lost_reason.isna()).sum(), E.pipeline_stage.eq("closed_lost").sum()),
        "held with ≥1 empty post-interview field": rate(E[E.entered_interview_held_at.notna()][checks.POST_FIELDS].isna().any(axis=1).sum(), E.entered_interview_held_at.notna().sum()),
        "duplicates / all rows": rate(L.is_duplicate.sum(), len(L)),
    })
    H = E[E.entered_interview_held_at.notna() & (E.entered_interview_held_at + pd.Timedelta(hours=48) <= ctx.SNAP)]
    pre = A[(A.actor_type == "advisor") & ~A.is_automated.astype(bool)].merge(H[["lead_id", "entered_interview_held_at"]], on="lead_id")
    return {"indicators": indicators, "followup": {k: FU[k] for k in ("numerator", "denominator", "rate")},
            "followup_leads_with_pre_interview_activity": int(pre[pre.activity_at < pre.entered_interview_held_at].lead_id.nunique()),
            "open_by_stage": OP.pipeline_stage.value_counts().to_dict(),
            "open_deliberate_anomalies": int(OP.lead_id.isin(set(G.lead_id[G.issue_type.isin(["stalled", "untouched_manual"])])).sum())}


def finance(ctx: Context) -> dict:
    W = ctx.W
    summary = pd.Series({"enrollments": len(W), "gross list value €": W.list_price.sum(), "campaign discount €": W.campaign_discount.sum(),
                         "one-time discount €": W.one_time_discount.sum(), "net price €": W.net_price.sum(),
                         "average net price €": W.net_price.mean()})
    bp = W.groupby("payment_type").agg(enrollments=("lead_id", "size"), avg_net=("net_price", "mean"), total_net=("net_price", "sum"))
    bp["mix"] = bp.enrollments / bp.enrollments.sum()
    grid = pd.crosstab(W.campaign_discount, W.payment_type, values=W.net_price, aggfunc="mean")
    return {"summary": summary, "by_payment_type": bp, "price_grid": grid}


def key_figures(ctx: Context) -> dict:
    """Raw values of the headline figures (formatted by the notebook)."""
    EM = ctx.EM
    return {"eligible_leads": len(ctx.E), "mature_eligible_leads": len(EM),
            "main_kpi": EM.has_held.mean(),
            "main_kpi_manual": EM.loc[EM.entry_path == "manual", "has_held"].mean(),
            "main_kpi_bot": EM.loc[EM.entry_path == "bot_booked", "has_held"].mean(),
            "show_rate_per_appointment": appointment_metrics(ctx)["rates"].iloc[0],
            "forms_over_held": directional_rates(ctx).iloc[0],
            "enrollments_over_held": directional_rates(ctx).iloc[1],
            "sla_24h_manual": sla_summary(ctx)["manual: first attempt ≤ 24 h"],
            "advisor_months_over_150_realised": workload(ctx)["over_150_realised"],
            "average_net_price": finance(ctx)["summary"]["average net price €"]}


# --------------------------------------------------------------------------- #
# Baseline metrics (47) — same definitions, order and rounding as v1.0.0-f0
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class MetricResult:
    id: str
    label_en: str
    label_es: str
    unit: str
    kind: str
    population: str
    numerator: str
    denominator: str | None
    time_basis: str
    section: int
    value: object
    numerator_value: object = None
    denominator_value: object = None

    def to_dict(self) -> dict:
        """Exactly the F0 JSON schema and key order."""
        v = self.value
        return {"id": self.id, "label_en": self.label_en, "label_es": self.label_es, "unit": self.unit, "kind": self.kind,
                "population": self.population, "numerator": self.numerator, "denominator": self.denominator,
                "time_basis": self.time_basis,
                "definition_ref": [f"{KPI_EN} §{self.section}", f"{KPI_ES} §{self.section}"],
                "numerator_value": None if self.numerator_value is None else int(self.numerator_value),
                "denominator_value": None if self.denominator_value is None else int(self.denominator_value),
                "value": None if v is None or pd.isna(v) else (int(v) if self.kind == "count" else round(float(v), 6))}


def baseline_metrics(ctx: Context) -> list[MetricResult]:
    """The 47 baseline metrics, in the order of baseline/metrics_v1.json."""
    E, EM, L, RX, M, Mw, OP, W = ctx.E, ctx.EM, ctx.L, ctx.RX, ctx.M, ctx.Mw, ctx.OP, ctx.W
    show, IE = ctx.show, ctx.IE
    showlead, s2, b = ctx.showlead, ctx.personal_wa_appointments, ctx.bot_pre
    LO, nur, ov, FU = ctx.lost, ctx.nurture, ctx.overdue_leads, ctx.followup
    work, expected = ctx.workload_frames
    cyc = _cycle_days(ctx)
    B, conf, human = b["B"], b["conf"], b["human"]
    full, nr = nur["full"], nur["nr"]
    out: list[MetricResult] = []

    def add(mid, label_en, label_es, unit, kind, population, numerator, denominator, time_basis, section,
            value, num=None, den=None):
        out.append(MetricResult(mid, label_en, label_es, unit, kind, population, numerator, denominator, time_basis,
                                section, value, num, den))

    ELIG = "eligible leads (is_duplicate = false, is_reactivation = false)"
    MAT = "mature eligible leads (snapshot_date − created_at ≥ 60 × 24 h)"
    COH = "cohort by created_at month; mature leads only"
    SNAPB = "state at snapshot_date"
    EMm, EMb = EM[EM.entry_path == "manual"], EM[EM.entry_path == "bot_booked"]
    Mwk, Mwe = Mw[~Mw.weekend_arrival], Mw[Mw.weekend_arrival]
    held_n = int(EM.entered_interview_held_at.notna().sum())
    form_n = int(EM.entered_form_completed_at.notna().sum())
    lost_r = LO[LO.lost_reason.notna()]
    sh_m, sh_b = show[show.entry_path == "manual"], show[show.entry_path == "bot_booked"]
    pwa = s2[s2.personal_wa]; pwn = s2[~s2.personal_wa]

    add("eligible_leads", "Eligible leads", "Leads elegibles", "lead", "count", ELIG, "count of rows", None, "12 months, all cohorts", 0, len(E), len(E))
    add("mature_eligible_leads", "Mature eligible leads", "Leads elegibles maduros", "lead", "count", MAT, "count of rows", None, "all cohorts", 0, len(EM), len(EM))
    add("duplicate_rows", "Duplicate rows", "Filas duplicadas", "lead", "count", "rows with is_duplicate = true", "count of rows", None, "12 months", 7, L.is_duplicate.sum(), L.is_duplicate.sum())
    add("reactivation_rows", "Reactivated leads", "Leads reactivados", "lead", "count", "rows with is_reactivation = true", "count of rows", None, "12 months", 6, len(RX), len(RX))
    add("share_manual_route", "Share of manual route", "Proporción ruta manual", "lead", "rate", ELIG, "entry_path = manual", "eligible leads", "12 months", 3, (E.entry_path == "manual").mean(), (E.entry_path == "manual").sum(), len(E))
    add("main_kpi_interviews_held_over_opportunities", "Main KPI: interviews held / opportunities", "KPI principal: entrevistas realizadas / oportunidades", "lead", "rate", MAT + ", both routes", "leads with ≥1 held appointment", "all mature eligible leads", COH, 1, EM.has_held.mean(), EM.has_held.sum(), len(EM))
    add("held_rate_manual_route", "Held interview rate, manual route", "Entrevista realizada, ruta manual", "lead", "rate", MAT + ", entry_path = manual", "leads with ≥1 held appointment", "mature eligible manual leads", COH, 1, EMm.has_held.mean(), EMm.has_held.sum(), len(EMm))
    add("held_rate_bot_route", "Held interview rate, bot route", "Entrevista realizada, ruta bot", "lead", "rate", MAT + ", entry_path = bot_booked", "leads with ≥1 held appointment", "mature eligible bot-route leads", COH, 1, EMb.has_held.mean(), EMb.has_held.sum(), len(EMb))
    add("booking_rate", "Booking rate", "Tasa de reserva", "lead", "rate", MAT, "leads with entered_interview_booked_at", "mature eligible leads", COH, 1, EM.entered_interview_booked_at.notna().mean(), EM.entered_interview_booked_at.notna().sum(), len(EM))
    add("show_rate_per_appointment", "Per-appointment show rate", "Show rate por cita", "appointment", "rate", "eligible appointments: eligible lead, not replaced, scheduled ≤ snapshot", "held appointments", "held + no_show appointments", "period (all appointment months)", 1, (show.interview_outcome == "held").mean(), (show.interview_outcome == "held").sum(), len(show))
    add("show_rate_per_appointment_manual", "Per-appointment show rate, manual route", "Show rate por cita, ruta manual", "appointment", "rate", "eligible appointments of manual-route leads", "held appointments", "held + no_show appointments", "period", 1, (sh_m.interview_outcome == "held").mean(), (sh_m.interview_outcome == "held").sum(), len(sh_m))
    add("show_rate_per_appointment_bot", "Per-appointment show rate, bot route", "Show rate por cita, ruta bot", "appointment", "rate", "eligible appointments of bot-route leads", "held appointments", "held + no_show appointments", "period", 1, (sh_b.interview_outcome == "held").mean(), (sh_b.interview_outcome == "held").sum(), len(sh_b))
    add("show_rate_per_lead", "Per-lead show rate", "Show rate por lead", "lead", "rate", MAT + " with ≥1 eligible appointment held or no_show", "leads with ≥1 held appointment", "leads with ≥1 eligible appointment held or no_show", COH, 1, showlead.mean(), showlead.sum(), len(showlead))
    add("cancellation_rate", "Cancellation rate", "Tasa de cancelación", "appointment", "rate", "eligible appointments with a terminal outcome", "cancelled appointments", "held + no_show + cancelled appointments", "period", 1, (IE.interview_outcome == "cancelled").mean(), (IE.interview_outcome == "cancelled").sum(), len(IE))
    add("forms_over_interviews_held", "Forms completed / interviews held", "Formularios / entrevistas realizadas", "lead", "rate", MAT + " with a held interview", "leads with entered_form_completed_at", "leads with entered_interview_held_at", COH, 2, rate(form_n, held_n), form_n, held_n)
    add("enrollments_over_interviews_held", "Enrollments / interviews held", "Matrículas / entrevistas realizadas", "lead", "rate", MAT + " with a held interview", "leads with enrolled_at", "leads with entered_interview_held_at", COH, 2, rate(EM.enrolled_at.notna().sum(), held_n), EM.enrolled_at.notna().sum(), held_n)
    add("links_over_forms", "Enrollment links / forms", "Enlaces / formularios", "lead", "rate", MAT + " with a completed form", "leads with entered_enrollment_link_sent_at", "leads with entered_form_completed_at", COH, 2, rate(EM.entered_enrollment_link_sent_at.notna().sum(), form_n), EM.entered_enrollment_link_sent_at.notna().sum(), form_n)
    add("enrollments_over_eligible_leads", "Enrollments / eligible leads", "Matrículas / leads elegibles", "lead", "rate", MAT, "leads with enrolled_at", "mature eligible leads", COH, 2, EM.enrolled_at.notna().mean(), EM.enrolled_at.notna().sum(), len(EM))
    add("sales_cycle_median_days", "Sales cycle, median (days)", "Ciclo de venta, mediana (días)", "lead", "median", MAT + " enrolled", "enrolled_at − created_at in days", "enrolled mature leads", COH, 2, cyc.median(), None, len(cyc))
    add("sales_cycle_mean_days", "Sales cycle, mean (days)", "Ciclo de venta, media (días)", "lead", "mean", MAT + " enrolled", "enrolled_at − created_at in days", "enrolled mature leads", COH, 2, cyc.mean(), None, len(cyc))
    SLAP = "eligible manual leads created ≥ 24 h before the snapshot"
    add("sla_first_attempt_24h_manual", "Manual first attempt ≤ 24 calendar hours", "Primer intento manual ≤ 24 horas naturales", "lead", "rate", SLAP, "first_human_attempt_at − created_at ≤ 24 h", "all leads in the population (with or without attempt)", "period (12 months)", 3, (Mw.resp_h <= 24).mean(), (Mw.resp_h <= 24).sum(), len(Mw))
    add("sla_first_attempt_24h_manual_weekday", "Manual first attempt ≤ 24 h, weekday arrivals", "Primer intento ≤ 24 h, entradas entre semana", "lead", "rate", SLAP + ", created Mon–Fri", "first attempt ≤ 24 h", "population", "period", 3, (Mwk.resp_h <= 24).mean(), (Mwk.resp_h <= 24).sum(), len(Mwk))
    add("sla_first_attempt_24h_manual_weekend", "Manual first attempt ≤ 24 h, weekend arrivals", "Primer intento ≤ 24 h, entradas en fin de semana", "lead", "rate", SLAP + ", created Sat–Sun", "first attempt ≤ 24 h", "population", "period", 3, (Mwe.resp_h <= 24).mean(), (Mwe.resp_h <= 24).sum(), len(Mwe))
    add("sla_first_attempt_same_day_manual", "Manual first attempt same calendar day", "Primer intento el mismo día natural", "lead", "rate", SLAP, "first attempt on the calendar date of created_at", "population", "period", 3, (Mw.first_human_attempt_at.dt.date == Mw.created_at.dt.date).mean(), (Mw.first_human_attempt_at.dt.date == Mw.created_at.dt.date).sum(), len(Mw))
    add("first_response_median_hours", "First response, median (calendar hours)", "Primera respuesta, mediana (horas naturales)", "lead", "median", SLAP + " with an attempt", "first_human_attempt_at − created_at", "leads with an attempt", "period", 3, Mw.resp_h.median(), None, Mw.resp_h.notna().sum())
    add("first_response_p90_hours", "First response, p90 (calendar hours)", "Primera respuesta, p90 (horas naturales)", "lead", "p90", SLAP + " with an attempt", "first_human_attempt_at − created_at", "leads with an attempt", "period", 3, Mw.resp_h.quantile(0.9), None, Mw.resp_h.notna().sum())
    att_all = E.first_human_attempt_at.notna()
    add("contact_rate", "Contact rate", "Tasa de contacto", "lead", "rate", ELIG + " with ≥1 human attempt", "leads with first_connected_at", "leads with ≥1 human attempt", "12 months", 3, E.first_connected_at[att_all].notna().mean(), E.first_connected_at[att_all].notna().sum(), att_all.sum())
    add("reassignment_rate_manual", "Reassignment rate (manual)", "Tasa de reasignación (manual)", "lead", "rate", "eligible manual leads", "reassigned_flag = true", "eligible manual leads", "12 months", 3, M.reassigned_flag.mean(), M.reassigned_flag.sum(), len(M))
    add("bot_pre_interview_confirmation", "Bot route: confirmation/reminder before first appointment", "Ruta bot: confirmación o recordatorio antes de la primera cita", "lead", "rate", "eligible bot-route leads", "leads with a bot pre_interview_reminder before the first appointment", "eligible bot-route leads", "12 months", 3, rate(len(conf), len(B)), len(conf), len(B))
    add("bot_pre_interview_human_contact", "Bot route: human contact before first appointment", "Ruta bot: contacto humano antes de la primera cita", "lead", "rate", "eligible bot-route leads", "leads with a manual advisor activity before the first appointment", "eligible bot-route leads", "12 months", 3, rate(len(human), len(B)), len(human), len(B))
    add("followup_48h_manual_advisor", "Manual advisor follow-up within 48 calendar hours", "Seguimiento manual del asesor en 48 horas naturales", "lead", "rate", "eligible leads whose first held interview + 48 h ≤ snapshot", "leads with ≥1 manual outbound advisor call/WhatsApp with held < activity_at ≤ held + 48 h", "eligible leads with a complete 48-hour window", "period (12 months)", 7, FU["rate"], FU["numerator"], FU["denominator"])
    add("open_leads_at_snapshot", "Open leads at snapshot", "Leads abiertos en la fecha de corte", "lead", "count", ELIG + ", stage not closed_won/closed_lost", "count", None, SNAPB, 7, len(OP), len(OP))
    add("open_without_next_task", "Open leads without next task", "Leads abiertos sin próxima tarea", "lead", "rate", "open eligible leads", "has_open_task = false", "open eligible leads", SNAPB, 7, (~OP.has_open_task.astype(bool)).mean(), (~OP.has_open_task.astype(bool)).sum(), len(OP))
    add("open_with_overdue_task", "Open leads with overdue task", "Leads abiertos con tarea vencida", "lead", "rate", "open eligible leads", "leads with ≥1 task in status overdue", "open eligible leads", SNAPB, 7, OP.lead_id.isin(ov).mean(), OP.lead_id.isin(ov).sum(), len(OP))
    lost_all = E.pipeline_stage.eq("closed_lost")
    add("closed_lost_without_reason", "Closed-lost without reason", "Cerrados perdidos sin motivo", "lead", "rate", "eligible closed-lost leads", "lost_reason is null", "closed-lost leads", SNAPB, 7, rate((lost_all & E.lost_reason.isna()).sum(), lost_all.sum()), (lost_all & E.lost_reason.isna()).sum(), lost_all.sum())
    add("lost_reason_share_iloc", "Share of ILOC among lost with reason", "Proporción ILOC entre perdidos con motivo", "lead", "rate", "eligible closed-lost leads with a reason", "lost_reason = iloc", "closed-lost leads with a reason", SNAPB, 6, (lost_r.lost_reason == "iloc").mean(), (lost_r.lost_reason == "iloc").sum(), len(lost_r))
    add("advisor_months_over_150_realised", "Advisor-months above 150 leads (realised)", "Meses-asesor por encima de 150 leads (realizados)", "advisor_month", "count", "eligible leads by first_owner_id and created_at month", "advisor-months with workload > 150", "all advisor-months", "period (month)", 5, (work > 150).sum().sum(), (work > 150).sum().sum(), work.size)
    add("advisor_months_over_150_expected", "Advisor-months above 150 leads (expected before randomness)", "Meses-asesor por encima de 150 (esperados antes del azar)", "advisor_month", "count", "scenario monthly volume × assignment weight", "advisor-months with expected workload > 150", "all advisor-months", "period (month)", 5, (expected > 150).sum().sum(), (expected > 150).sum().sum(), expected.size)
    add("enrollments_total", "Enrollments recorded by the snapshot", "Matrículas registradas hasta el corte", "deal", "count", ELIG + " with enrolled_at", "count", None, "period (12 months)", 8, len(W), len(W))
    add("avg_net_price_eur", "Average net price (EUR)", "Precio neto medio (EUR)", "deal", "mean", "enrolled eligible leads", "Σ net_price", "enrollments", "period", 8, W.net_price.mean(), None, len(W))
    add("avg_net_price_single_eur", "Average net price, single payment (EUR)", "Precio neto medio, pago único (EUR)", "deal", "mean", "enrolled eligible leads, payment_type = single", "Σ net_price", "single-payment enrollments", "period", 8, W.loc[W.payment_type == "single", "net_price"].mean(), None, (W.payment_type == "single").sum())
    add("avg_net_price_installments_eur", "Average net price, instalments (EUR)", "Precio neto medio, fraccionado (EUR)", "deal", "mean", "enrolled eligible leads, payment_type = installments", "Σ net_price", "instalment enrollments", "period", 8, W.loc[W.payment_type == "installments", "net_price"].mean(), None, (W.payment_type == "installments").sum())
    add("installments_share", "Share of instalment enrollments", "Proporción de matrículas fraccionadas", "deal", "rate", "enrolled eligible leads", "payment_type = installments", "enrollments", "period", 8, (W.payment_type == "installments").mean(), (W.payment_type == "installments").sum(), len(W))
    add("nurture_reactivation_complete_window", "Nurture reactivation (complete 150-day windows)", "Reactivación desde nurture (ventanas completas de 150 días)", "deal", "rate", "eligible deals that entered nurture ≥ 150 days before the snapshot", "nurture_end_reason = reactivated", "those deals", "period", 6, (full.nurture_end_reason == "reactivated").mean(), (full.nurture_end_reason == "reactivated").sum(), len(full))
    add("nurture_email_failure_rate", "Nurture emails not sent or failed", "Emails de nurture no enviados o fallidos", "email", "rate", "nurture emails recorded by the snapshot", "email_status in {not_sent, failed}", "nurture emails", "period", 6, nr.email_status.isin(["not_sent", "failed"]).mean(), nr.email_status.isin(["not_sent", "failed"]).sum(), len(nr))
    add("show_rate_with_personal_whatsapp", "Show rate with personal WhatsApp (association only)", "Show rate con WhatsApp personalizado (solo asociación)", "appointment", "rate", "eligible appointments held/no_show scheduled ≥ 2025-07-01, with a personal WhatsApp before the slot", "held", "held + no_show", "period (Jul–Dec)", 1, (pwa.interview_outcome == "held").mean(), (pwa.interview_outcome == "held").sum(), len(pwa))
    add("show_rate_without_personal_whatsapp", "Show rate without personal WhatsApp (association only)", "Show rate sin WhatsApp personalizado (solo asociación)", "appointment", "rate", "eligible appointments held/no_show scheduled ≥ 2025-07-01, without a personal WhatsApp", "held", "held + no_show", "period (Jul–Dec)", 1, (pwn.interview_outcome == "held").mean(), (pwn.interview_outcome == "held").sum(), len(pwn))
    return out


def baseline_document(ctx: Context, baseline_id: str, root: Path | None = None) -> dict:
    """Full metrics document with the F0 schema (metrics, cohorts, anomaly reconciliation, input hashes)."""
    root = Path(root) if root is not None else (ctx.root or ROOT)
    results, _ = ctx.check_results
    cohorts = [{"cohort": str(p), "eligible_leads": int(r.eligible_leads), "mature_leads": int(r.mature_leads),
                "mature_share": round(float(r.mature_share), 6), "label": r.label,
                "newest_lead_created_at": str(r.newest_lead_created_at), "min_age_days": float(r.min_age_days)}
               for p, r in ctx.cohorts.iterrows()]
    anoms = [{"anomaly": r.check, "injected": int(r.injected), "detectable": int(r.detectable), "detected": int(r.detected),
              "not_detectable": int(r.not_detectable), "rule": r.detail.split(" · ")[0]}
             for r in results[results.category == "anomaly"].itertuples()]
    return {
        "schema_version": "1.0",
        "baseline_id": baseline_id,
        "note": SYNTHETIC_NOTE,
        "seed": int(ctx.cfg["seed"]), "snapshot_date": str(ctx.SNAP), "maturity_days": ctx.maturity_days,
        "inputs_sha256": {p: sha256_file(root / p) for p in INPUT_FILES},
        "metrics": [m.to_dict() for m in baseline_metrics(ctx)], "cohort_maturity": cohorts, "anomaly_reconciliation": anoms,
        "logic_checks": {"count": int((results.category == "logic").sum()),
                         "violations": int(results.loc[results.category == "logic", "violations"].sum())},
    }


DESCRIPTIVE_FIELDS = ["label_en", "label_es", "unit", "kind", "population", "numerator", "denominator",
                      "time_basis", "definition_ref"]


def reconcile(document: dict, reference: dict) -> pd.DataFrame:
    """Metric-by-metric comparison of a metrics document with a reference (e.g. baseline/metrics_v1.json).

    Values are compared after the reference rounding (6 decimals) with no extra tolerance; counts, numerators and
    denominators must be equal integers; descriptive fields must be equal strings.
    """
    ref = {m["id"]: m for m in reference["metrics"]}
    order = {m["id"]: i for i, m in enumerate(reference["metrics"])}
    rows = []
    for pos, m in enumerate(document["metrics"]):
        r = ref.get(m["id"])
        get = (lambda k: None) if r is None else r.get
        # equality is decided on the original JSON values (None stays None; no float NaN comparisons)
        flags = {"position_equal": order.get(m["id"]) == pos,
                 "descriptive_equal": r is not None and all(m[f] == r[f] for f in DESCRIPTIVE_FIELDS),
                 "value_equal": r is not None and m["value"] == r["value"],
                 "numerator_equal": r is not None and m["numerator_value"] == r["numerator_value"],
                 "denominator_equal": r is not None and m["denominator_value"] == r["denominator_value"]}
        rows.append({"id": m["id"], "value_reference": get("value"), "value": m["value"],
                     "abs_diff": None if r is None or m["value"] is None or r["value"] is None else abs(m["value"] - r["value"]),
                     "numerator_reference": get("numerator_value"), "numerator": m["numerator_value"],
                     "denominator_reference": get("denominator_value"), "denominator": m["denominator_value"],
                     **flags, "match": all(flags.values())})
    cols = ["id", "value_reference", "value", "abs_diff", "numerator_reference", "numerator", "denominator_reference",
            "denominator", "position_equal", "descriptive_equal", "value_equal", "numerator_equal", "denominator_equal", "match"]
    out = pd.DataFrame(rows, columns=cols, dtype=object).set_index("id")
    missing = sorted(set(ref) - set(out.index))
    out.attrs["missing_from_document"] = missing
    return out


def reconciliation_summary(document: dict, reference: dict) -> dict:
    """Headline of the comparison with the reference: metric matches and identity of the other sections."""
    rec = reconcile(document, reference)
    other = ("cohort_maturity", "anomaly_reconciliation", "logic_checks", "inputs_sha256")
    return {"metrics": len(rec), "matching": int(rec.match.astype(bool).sum()),
            "missing_from_document": rec.attrs["missing_from_document"],
            "other_sections_identical": all(document[k] == reference[k] for k in other), "table": rec}
