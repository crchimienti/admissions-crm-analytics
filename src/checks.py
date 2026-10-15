"""Integrity checks for the synthetic admissions dataset.

Comprobaciones de integridad del dataset sintético.

Two categories:
* ``logic``   – must have zero violations; a violation is a generator bug.
* ``anomaly`` – deliberate, injected data-quality issues. Each is detected by a
  rule, reported, and compared with ``data/dq_ground_truth.csv``. A detection
  outside the injected set is a logic error.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from calendar_utils import add_business_days
except ImportError:  # pragma: no cover
    from src.calendar_utils import add_business_days

ROOT = Path(__file__).resolve().parents[1]

ADVISORS = {"ADV_01", "ADV_02", "ADV_03", "ADV_04", "ADV_05"}
STAGES = ["new_lead", "opportunity", "interview_booked", "interview_held", "form_completed",
          "enrollment_link_sent", "closed_won", "closed_lost"]
STAGE_TS = [("opportunity", "entered_opportunity_at"), ("interview_booked", "entered_interview_booked_at"),
            ("interview_held", "entered_interview_held_at"), ("form_completed", "entered_form_completed_at"),
            ("enrollment_link_sent", "entered_enrollment_link_sent_at"), ("closed_won", "enrolled_at"),
            ("closed_lost", "closed_lost_at")]
POST_FIELDS = ["candidate_situation", "immediate_interest", "program_interest", "decision_maker",
               "main_objection", "payment_preference", "next_step_agreed"]
ALLOWED = {
    "pipeline_stage": set(STAGES),
    "lead_status": {"new", "working", "iloc_sequence", "nurture", "closed_won", "closed_lost"},
    "last_interview_outcome": {"pending", "held", "no_show", "cancelled"},
    "lost_reason": {"iloc", "financial", "official_qualification", "future_intake"},
    "entry_path": {"bot_booked", "manual"},
    "channel_group": {"paid_social", "webinar", "web_direct", "organic", "referral", "event", "partner"},
    "candidate_profile": {"healthcare", "non_healthcare"},
    "program_alias": {"PRG_A", "PRG_B", "PRG_C", "PRG_D"},
    "iloc_end_reason": {"responded", "booked", "closed_iloc"},
    "nurture_end_reason": {"reactivated", "window_ended"},
    "payment_type": {"single", "installments"},
    "candidate_situation": {"employed", "unemployed", "student", "career_change"},
    "immediate_interest": {"high", "medium", "low"},
    "program_interest": {"high", "medium", "low"},
    "decision_maker": {"self", "shared", "other"},
    "main_objection": {"price", "time", "official_qualification", "timing", "none"},
    "payment_preference": {"single", "installments", "undecided"},
}
ALLOWED_ACT = {
    "actor_type": {"advisor", "bot", "system", "candidate"},
    "activity_type": {"call", "whatsapp", "email", "interview", "task", "note"},
    "direction": {"outbound", "inbound", "internal"},
    "sequence_name": {"none", "booking", "first_contact", "iloc", "reschedule", "pre_interview_reminder",
                      "post_interview", "form_reminder", "form", "enrollment", "nurture"},
    "call_outcome": {"connected", "no_answer", "voicemail", "wrong_number"},
    "email_status": {"sent", "not_sent", "failed"},
    "interview_outcome": {"pending", "held", "no_show", "rescheduled", "cancelled"},
    "task_status": {"open", "overdue", "done", "cancelled"},
}

LEAD_TS = ["created_at", "reassigned_at", "first_human_attempt_at", "first_connected_at",
           "entered_opportunity_at", "entered_interview_booked_at", "entered_interview_held_at",
           "entered_form_completed_at", "entered_enrollment_link_sent_at", "enrolled_at", "closed_lost_at",
           "iloc_started_at", "iloc_ended_at", "nurture_started_at", "nurture_ended_at", "next_task_due_at",
           "snapshot_date"]
ACT_TS = ["activity_at", "interview_scheduled_for", "task_due_at", "task_completed_at"]


def load(data_dir: Path = ROOT / "data"):
    leads = pd.read_csv(data_dir / "leads.csv")
    acts = pd.read_csv(data_dir / "activities.csv")
    gt = pd.read_csv(data_dir / "dq_ground_truth.csv")
    for c in LEAD_TS:
        leads[c] = pd.to_datetime(leads[c])
    for c in ACT_TS:
        acts[c] = pd.to_datetime(acts[c])
    return leads, acts, gt


def _same(a, b):
    if a is None or pd.isna(a):
        return b is None or pd.isna(b)
    return not pd.isna(b) and a == b


@dataclass
class Result:
    check: str
    category: str      # logic | anomaly | governance
    violations: int
    detail: str = ""
    sample: str = ""
    injected: float = np.nan
    detectable: float = np.nan
    detected: float = np.nan
    not_detectable: float = np.nan
    note: str = ""


class Checker:
    def __init__(self, leads, acts, gt):
        self.L, self.A, self.G = leads, acts, gt
        self.snap = leads["snapshot_date"].iloc[0]
        self.nd = leads[~leads.is_duplicate].copy()            # non-duplicate rows
        self.results: list[Result] = []
        self.warnings: list[str] = []

    # -- helpers -------------------------------------------------------- #
    def logic(self, name, mask_or_ids, detail=""):
        ids = self._ids(mask_or_ids)
        self.results.append(Result(name, "logic", len(ids), detail, ", ".join(map(str, ids[:5]))))

    @staticmethod
    def _ids(x):
        return sorted({str(i) for i in x})

    def anomaly(self, issue, rule, detected: set, injected: set, detectable: set | None = None,
                note="", rate=None, expected=None):
        """Compare a detection rule with the ground truth.

        ``detectable`` is the subset of injected cases the rule can observe at the
        snapshot (default: all injected). Logic requires detected == detectable.
        """
        detectable = injected if detectable is None else detectable
        assert detectable <= injected
        extra, missing = detected - detectable, detectable - detected
        self.results.append(Result(f"{issue}: detected but not injected", "logic", len(extra),
                                   sample=", ".join(sorted(extra)[:5])))
        self.results.append(Result(f"{issue}: injected and detectable but not detected", "logic", len(missing),
                                   sample=", ".join(sorted(missing)[:5])))
        det = rule
        if rate is not None:
            det += f" · observed rate {rate:.3f}"
            if expected is not None:
                det += f" (scenario parameter {expected:.3f})"
                if expected > 0 and not (0.5 * expected <= rate <= 1.5 * expected):
                    self.warnings.append(f"{issue}: observed rate {rate:.3f} far from parameter {expected:.3f}")
        self.results.append(Result(issue, "anomaly", len(detected), det, injected=len(injected),
                                   detectable=len(detectable), detected=len(detected),
                                   not_detectable=len(injected) - len(detectable), note=note))

    # -- checks --------------------------------------------------------- #
    def run(self):
        for fn in (self.schema, self.identity, self.states, self.dates, self.pricing, self.iloc_calendar,
                   self.appointments, self.leads_vs_activities, self.anomalies):
            fn()
        return pd.DataFrame([r.__dict__ for r in self.results])

    def schema(self):
        L, A = self.L, self.A
        self.logic("lead_id unique", L.lead_id[L.lead_id.duplicated()])
        self.logic("activity_id unique", A.activity_id[A.activity_id.duplicated()])
        bad = []
        for col, allowed in ALLOWED.items():
            v = L[col].dropna()
            if col == "next_step_agreed":
                continue
            bad += list(L.loc[v[~v.astype(str).isin(allowed)].index, "lead_id"])
        self.logic("lead enum values allowed", bad)
        bad = []
        for col, allowed in ALLOWED_ACT.items():
            v = A[col].dropna()
            bad += list(A.loc[v[~v.astype(str).isin(allowed)].index, "lead_id"])
        self.logic("activity enum values allowed", bad)
        self.logic("is_synthetic always true", L.lead_id[~L.is_synthetic.astype(bool)])

    def identity(self):
        L = self.L.sort_values(["person_key", "created_at"])
        self.logic("person_key present for all leads", L.lead_id[L.person_key.isna()])
        # duplicate detection rule (§2.4): not a reactivation and an earlier
        # non-duplicate row of the same person created <= 14 days before
        base = self.L[["lead_id", "person_key", "created_at", "is_reactivation"]]
        prev = self.L.loc[~self.L.is_duplicate, ["lead_id", "person_key", "created_at"]]
        m = base.merge(prev, on="person_key", suffixes=("", "_prev"))
        m = m[(m.lead_id != m.lead_id_prev) & ~m.is_reactivation
              & (m.created_at >= m.created_at_prev)
              & (m.created_at - m.created_at_prev <= pd.Timedelta(days=14))]
        rule = self.L.lead_id.isin(set(m.lead_id))
        self.logic("is_duplicate matches the 14-day detection rule", self.L.lead_id[rule != self.L.is_duplicate.astype(bool)])
        D = self.L[self.L.is_duplicate]
        life = [c for _, c in STAGE_TS] + ["first_human_attempt_at", "first_connected_at", "entry_path", "lost_reason"]
        self.logic("duplicates carry no lifecycle (stage new_lead, status new, no activities)",
                   list(D.lead_id[(D.pipeline_stage != "new_lead") | (D.lead_status != "new") | D[life].notna().any(axis=1)])
                   + list(set(self.A.lead_id) & set(D.lead_id)))
        # one original row per person
        orig = self.L[~self.L.is_duplicate & ~self.L.is_reactivation]
        self.logic("one original lead per person", orig.lead_id[orig.person_key.duplicated(keep=False)])
        # reactivations
        R = self.L[self.L.is_reactivation]
        P = self.L.set_index("lead_id")
        bad = []
        for _, r in R.iterrows():
            pid = r.reactivated_from_lead_id
            if pid not in P.index:
                bad.append(r.lead_id); continue
            p = P.loc[pid]
            days = (r.created_at - p.closed_lost_at).total_seconds() / 86400
            if (p.person_key != r.person_key or p.lost_reason != "future_intake" or p.nurture_end_reason != "reactivated"
                    or abs((p.nurture_ended_at - r.created_at).total_seconds()) > 1 or not (30 <= days <= 150)
                    or r.entry_path != "manual" or r.is_duplicate or p.is_reactivation):
                bad.append(r.lead_id)
        self.logic("reactivations link to a nurture deal of the same person (30-150 days)", bad)
        self.logic("non-reactivations have no parent", self.L.lead_id[~self.L.is_reactivation & self.L.reactivated_from_lead_id.notna()])
        # a person never has a nurture deal and an open deal at the same time
        nd = self.nd
        open_p = set(nd.person_key[~nd.pipeline_stage.isin(["closed_won", "closed_lost"])])
        nur_p = set(nd.person_key[nd.lead_status == "nurture"])
        self.logic("no person with a nurture deal and an open deal", sorted(open_p & nur_p))

    def states(self):
        L = self.nd
        won = L.pipeline_stage == "closed_won"
        lost = L.pipeline_stage == "closed_lost"
        self.logic("R1 closed_won <=> status closed_won <=> enrolled_at",
                   L.lead_id[(won != (L.lead_status == "closed_won")) | (won != L.enrolled_at.notna()) | (won & L.lost_reason.notna())])
        self.logic("R2 closed_lost <=> status in {closed_lost, nurture} <=> closed_lost_at",
                   L.lead_id[(lost != L.lead_status.isin(["closed_lost", "nurture"])) | (lost != L.closed_lost_at.notna())])
        self.logic("R3 lost_reason only on closed_lost", L.lead_id[L.lost_reason.notna() & ~lost])
        iloc_close = (L.iloc_end_reason == "closed_iloc") & (L.iloc_ended_at == L.closed_lost_at)
        self.logic("R3 exception scope: null lost_reason never in nurture / ILOC closure",
                   L.lead_id[lost & L.lost_reason.isna() & ((L.lead_status != "closed_lost") | iloc_close | L.nurture_started_at.notna())])
        self.logic("R4 nurture => closed_lost & future_intake",
                   L.lead_id[(L.lead_status == "nurture") & (~lost | (L.lost_reason != "future_intake"))])
        self.logic("R5 iloc_sequence => opportunity/interview_booked, started, not ended",
                   L.lead_id[(L.lead_status == "iloc_sequence") & (~L.pipeline_stage.isin(["opportunity", "interview_booked"])
                             | L.iloc_started_at.isna() | L.iloc_ended_at.notna())])
        self.logic("R6 lost_reason iloc => closed_iloc at closed_lost_at",
                   L.lead_id[(L.lost_reason == "iloc") & ~iloc_close])
        self.logic("R7 status new => manual, new_lead/opportunity, no human attempt",
                   L.lead_id[(L.lead_status == "new") & ((L.entry_path != "manual") | ~L.pipeline_stage.isin(["new_lead", "opportunity"])
                                                         | L.first_human_attempt_at.notna())])
        self.logic("R8 entered_opportunity_at present iff manual route",
                   L.lead_id[(L.entry_path == "manual") != L.entered_opportunity_at.notna()])
        # R10: open with last outcome no_show stays interview_booked
        open_ = ~L.pipeline_stage.isin(["closed_won", "closed_lost"])
        self.logic("R10 no-show keeps the lead in interview_booked",
                   L.lead_id[open_ & (L.last_interview_outcome == "no_show") & (L.pipeline_stage != "interview_booked")])
        self.logic("R12 pricing fields only on closed_won",
                   L.lead_id[~won & L[["payment_type", "list_price", "campaign_discount", "one_time_discount", "net_price"]].notna().any(axis=1)])
        # stage = last reached stage
        exp = []
        for _, r in L.iterrows():
            s = "new_lead"
            for name, col in STAGE_TS[:5]:
                if pd.notna(r[col]):
                    s = name
            if pd.notna(r.enrolled_at):
                s = "closed_won"
            elif pd.notna(r.closed_lost_at):
                s = "closed_lost"
            if s != r.pipeline_stage:
                exp.append(r.lead_id)
        self.logic("R9 pipeline_stage = last stage reached", exp)
        self.logic("lead_status values consistent with open/closed",
                   L.lead_id[open_ & L.lead_status.isin(["closed_won", "closed_lost", "nurture"])])

    def dates(self):
        L = self.nd
        ts = [c for c in LEAD_TS if c not in ("snapshot_date", "next_task_due_at")]
        self.logic("lead timestamps <= snapshot", L.lead_id[(L[ts] > self.snap).any(axis=1)])
        self.logic("activity_at <= snapshot", self.A.lead_id[self.A.activity_at > self.snap])
        order = [c for _, c in STAGE_TS[:6]]
        bad = []
        arr = L[["created_at"] + order].to_numpy()
        for i, row in enumerate(arr):
            vals = [v for v in row if pd.notna(v)]
            if any(b < a for a, b in zip(vals, vals[1:])):
                bad.append(L.lead_id.iloc[i])
        self.logic("R9 stage timestamps non-decreasing in funnel order", bad)
        reached = L[order].max(axis=1)
        self.logic("closed_lost_at >= last stage reached", L.lead_id[L.closed_lost_at.notna() & (L.closed_lost_at < reached)])
        self.logic("first attempt / first connection after creation",
                   L.lead_id[(L.first_human_attempt_at < L.created_at) | (L.first_connected_at < L.created_at)])
        R = L[L.reassigned_flag.astype(bool)]
        self.logic("reassignment: >= 24 h after creation, different owner, before first attempt",
                   R.lead_id[(R.reassigned_at < R.created_at + pd.Timedelta(hours=24)) | (R.current_owner_id == R.first_owner_id)
                             | (R.first_human_attempt_at.notna() & (R.first_human_attempt_at < R.reassigned_at))])
        nr = L[~L.reassigned_flag.astype(bool)]
        self.logic("not reassigned => current owner = first owner", nr.lead_id[nr.current_owner_id != nr.first_owner_id])
        mg = self.A.merge(self.L[["lead_id", "created_at"]], on="lead_id")
        self.logic("activities after lead creation", mg.lead_id[mg.activity_at < mg.created_at])

    def pricing(self):
        W = self.nd[self.nd.pipeline_stage == "closed_won"]
        single = W.payment_type == "single"
        exp_one = np.where(single, ((W.list_price - W.campaign_discount) * 0.15).round(2), 0.0)
        bad = W.lead_id[(W.list_price != 3200) | ~W.campaign_discount.isin([600, 500, 350])
                        | ((W.one_time_discount - exp_one).abs() > 0.005)
                        | ((W.net_price - (W.list_price - W.campaign_discount - W.one_time_discount)).abs() > 0.005)
                        | (single & ((W.net_price - (3200 - W.campaign_discount) * 0.85).abs() > 0.005))
                        | (~single & ((W.net_price - (3200 - W.campaign_discount)).abs() > 0.005))]
        self.logic("pricing formula (single: (3200-d)*0.85; installments: 3200-d)", bad)

    def iloc_calendar(self):
        A = self.A[(self.A.sequence_name == "iloc") & self.A.business_day_index.notna()].copy()
        key = ["lead_id", "sequence_instance"]
        bd0 = (A[(A.business_day_index == 0) & (A.activity_type != "task")]
               .groupby(key).activity_at.min().dt.date.rename("bd0"))
        A = A.join(bd0, on=key)
        ref = np.where(A.activity_type == "task", A.task_due_at.dt.date, A.activity_at.dt.date)
        expected = [add_business_days(d, int(i)) if pd.notna(d) else None
                    for d, i in zip(A.bd0, A.business_day_index)]
        bad_row = (A.bd0.isna() | (A.business_day_index == 1) | (pd.Series(ref, index=A.index) != pd.Series(expected, index=A.index))
                   | ((A.activity_type == "task") & (A.activity_at.dt.date != A.bd0))
                   | ((A.business_day_index == 6) & (A.activity_type != "note")))
        self.logic("ILOC steps on BD0..BD5 business days, no BD1 action, close note on BD6", A.lead_id[bad_row])
        L = self.nd[self.nd.lost_reason == "iloc"]
        exp6 = [add_business_days(d, 6) for d in L.iloc_started_at.dt.date]
        self.logic("ILOC closure on the 6th business day after BD0",
                   L.lead_id[L.closed_lost_at.dt.date.to_numpy() != np.array(exp6, dtype=object)])
        self.logic("no ILOC outbound activity on weekends",
                   A.lead_id[(A.activity_type != "task") & (A.activity_at.dt.weekday >= 5)])

    def appointments(self):
        I = self.A[self.A.activity_type == "interview"].copy()
        snap = self.snap
        self.logic("pending <=> scheduled after the snapshot",
                   I.lead_id[(I.interview_outcome == "pending") != (I.interview_scheduled_for > snap)])
        ids = set(I.activity_id)
        resch = I[I.interview_outcome == "rescheduled"]
        child = I.set_index("activity_id")
        bad = list(resch.lead_id[resch.replaced_by_activity_id.isna() | ~resch.replaced_by_activity_id.isin(ids)])
        for _, r in resch[resch.replaced_by_activity_id.isin(ids)].iterrows():
            c = child.loc[r.replaced_by_activity_id]
            if c.rescheduled_from_activity_id != r.activity_id or c.lead_id != r.lead_id:
                bad.append(r.lead_id)
        bad += list(I.lead_id[I.replaced_by_activity_id.notna() & (I.interview_outcome != "rescheduled")])
        self.logic("rescheduled <=> replaced by a linked replacement appointment", bad)
        rb = I[I.rebooked_after_activity_id.notna()]
        bad = [r.lead_id for _, r in rb.iterrows()
               if r.rebooked_after_activity_id not in child.index
               or child.at[r.rebooked_after_activity_id, "interview_outcome"] not in ("no_show", "cancelled")
               or child.at[r.rebooked_after_activity_id, "lead_id"] != r.lead_id]
        self.logic("new bookings follow a no_show / cancelled appointment of the same lead", bad)
        self.logic("at most 3 appointments per lead", [k for k, v in I.groupby("lead_id").size().items() if v > 3])
        L = self.nd.set_index("lead_id")
        held = I[I.interview_outcome == "held"].groupby("lead_id").interview_scheduled_for.min()
        has_held = L.entered_interview_held_at.notna()
        bad = list(set(held.index) ^ set(L.index[has_held]))
        common = held.index.intersection(L.index[has_held])
        bad += list(common[(held[common] != L.loc[common, "entered_interview_held_at"])])
        self.logic("R11 held appointment <=> entered_interview_held_at (= first held)", bad)
        first_book = I.groupby("lead_id").activity_at.min()
        hb = L.entered_interview_booked_at.notna()
        bad = list(set(first_book.index) ^ set(L.index[hb]))
        common = first_book.index.intersection(L.index[hb])
        bad += list(common[first_book[common] != L.loc[common, "entered_interview_booked_at"]])
        self.logic("entered_interview_booked_at = first booking", bad)
        last = (I[I.replaced_by_activity_id.isna()].sort_values(["activity_at", "activity_id"])
                .groupby("lead_id").interview_outcome.last())
        lio = L.last_interview_outcome
        bad = [lid for lid in L.index if (lio[lid] if pd.notna(lio[lid]) else None) != last.get(lid)]
        self.logic("R11 last_interview_outcome = last non-replaced appointment", bad)

    def leads_vs_activities(self):
        A, L = self.A, self.L
        self.logic("every activity belongs to a lead", A.lead_id[~A.lead_id.isin(L.lead_id)])
        adv = A.actor_type == "advisor"
        self.logic("advisor activities carry a valid actor_id; others none",
                   A.lead_id[(adv & ~A.actor_id.isin(ADVISORS)) | (~adv & A.actor_id.notna())])
        man = A[adv & (A.direction == "outbound") & A.activity_type.isin(["call", "whatsapp"]) & ~A.is_automated.astype(bool)]
        fa = man.groupby("lead_id").activity_at.min()
        Li = self.nd.set_index("lead_id")
        got = Li.first_human_attempt_at
        bad = [lid for lid in Li.index if not _same(fa.get(lid), got[lid])]
        self.logic("first_human_attempt_at = first manual advisor call/WhatsApp", bad)
        conn = pd.concat([A.loc[(A.activity_type == "call") & (A.call_outcome == "connected"), ["lead_id", "activity_at"]],
                          A.loc[A.direction == "inbound", ["lead_id", "activity_at"]],
                          A.loc[(A.activity_type == "interview") & (A.interview_outcome == "held"),
                                ["lead_id", "interview_scheduled_for"]].rename(columns={"interview_scheduled_for": "activity_at"})])
        fc = conn.groupby("lead_id").activity_at.min()
        gc = Li.first_connected_at
        bad = [lid for lid in Li.index if not _same(fc.get(lid), gc[lid])]
        self.logic("first_connected_at = first connected call / inbound reply / held interview", bad)
        T = A[A.activity_type == "task"]
        self.logic("task_status consistent with due date and snapshot",
                   T.lead_id[((T.task_status == "overdue") != (T.task_status.isin(["open", "overdue"]) & (T.task_due_at < self.snap)))
                             | ((T.task_status == "done") != T.task_completed_at.notna())])
        ot = T[T.task_status.isin(["open", "overdue"])]
        has = set(ot.lead_id)
        nxt = ot.groupby("lead_id").task_due_at.min()
        bad = [lid for lid in Li.index if (lid in has) != bool(Li.at[lid, "has_open_task"])
               or (lid in has and nxt[lid] != Li.at[lid, "next_task_due_at"])
               or (lid not in has and pd.notna(Li.at[lid, "next_task_due_at"]))]
        self.logic("has_open_task / next_task_due_at match open tasks", bad)
        closed = set(Li.index[Li.pipeline_stage.isin(["closed_won", "closed_lost"])])
        self.logic("closed leads have no open tasks", sorted(has & closed))
        term = Li.enrolled_at.fillna(Li.closed_lost_at)
        mg = A[A.sequence_name != "nurture"].merge(term.rename("term"), left_on="lead_id", right_index=True)
        self.logic("no activity after closing (except nurture; won: confirmation within 1 h)",
                   mg.lead_id[mg.term.notna() & (mg.activity_at > mg.term + pd.Timedelta(hours=1))])
        N = A[A.sequence_name == "nurture"].merge(Li[["nurture_started_at", "nurture_ended_at"]], left_on="lead_id", right_index=True)
        self.logic("nurture emails only inside the nurture window",
                   N.lead_id[N.nurture_started_at.isna() | (N.activity_at < N.nurture_started_at)
                             | (N.nurture_ended_at.notna() & (N.activity_at >= N.nurture_ended_at))])
        self.logic("post-interview fields only after an interview held",
                   Li.index[Li.entered_interview_held_at.isna() & Li[POST_FIELDS].notna().any(axis=1)])

    def anomalies(self):
        G, L, A = self.G, self.nd, self.A
        inj = lambda t: set(G.lead_id[G.issue_type == t])
        open_ = ~L.pipeline_stage.isin(["closed_won", "closed_lost"])
        lost = L.pipeline_stage == "closed_lost"

        det = set(L.lead_id[lost & L.lost_reason.isna()])
        self.anomaly("missing_lost_reason", "closed_lost with null lost_reason", det, inj("missing_lost_reason"),
                     rate=len(det) / max(lost.sum(), 1), expected=0.03)

        # open without task: the parameter applies to open leads with no pending sequence task
        seq_open = set(A.lead_id[(A.activity_type == "task") & A.task_status.isin(["open", "overdue"])
                                 & (A.sequence_name == "iloc")])
        pool = open_ & ~L.lead_id.isin(seq_open)
        det = set(L.lead_id[open_ & ~L.has_open_task.astype(bool)])
        self.anomaly("open_without_task", "open lead with has_open_task = false", det, inj("open_without_task"),
                     rate=len(det) / max(pool.sum(), 1), expected=0.08,
                     note="rate over open leads without a pending ILOC task (the pool the parameter applies to)")

        # overdue tasks: same unit as the ground truth (lead whose follow-up task is overdue)
        T = A[A.activity_type == "task"]
        det = set(T.lead_id[T.task_status == "overdue"])
        stalled = inj("stalled")
        fu = T[(T.sequence_step == "next_step") & ~T.lead_id.isin(stalled)]
        self.anomaly("overdue_task", "lead with >= 1 task in status overdue", det, inj("overdue_task"),
                     rate=(fu.task_status == "overdue").mean() if len(fu) else None, expected=0.15,
                     note="rate over follow-up tasks of non-stalled open leads; stalled leads always carry an overdue task")

        hp = L.entered_interview_held_at.notna()
        det = set(L.lead_id[hp & L[POST_FIELDS].isna().any(axis=1)])
        self.anomaly("empty_post_interview_fields", "held lead with >= 1 null post-interview field", det,
                     inj("empty_post_interview_fields"), rate=len(det) / max(hp.sum(), 1), expected=0.10)

        det = set(self.L.lead_id[self.L.is_duplicate])
        self.anomaly("duplicate", "is_duplicate = true (14-day person rule)", det, inj("duplicate"),
                     rate=len(det) / max(len(self.L) - len(det), 1), expected=0.02)

        man = L.entry_path == "manual"
        old = set(L.lead_id[L.created_at <= self.snap - pd.Timedelta(days=10)])
        det = set(L.lead_id[man & open_ & L.first_human_attempt_at.isna()]) & old
        injected = inj("untouched_manual")
        self.anomaly("untouched_manual", "open manual lead, no human attempt, created >= 10 days before snapshot",
                     det, injected, injected & old, rate=len(injected) / max(man.sum(), 1), expected=0.02,
                     note="not detectable: created < 10 days before the snapshot, indistinguishable from leads still awaiting a first attempt")

        # stage change without its dedicated support record (same unit as the ground truth)
        recs = {
            "opportunity": A[A.sequence_step == "bot_booking_attempt"][["lead_id", "activity_at"]],
            "interview_booked": A[A.activity_type == "interview"][["lead_id", "activity_at"]],
            "interview_held": A[(A.activity_type == "interview") & (A.interview_outcome == "held")]
                [["lead_id", "interview_scheduled_for"]].rename(columns={"interview_scheduled_for": "activity_at"}),
            "form_completed": A[A.sequence_step == "form_received"][["lead_id", "activity_at"]],
            "enrollment_link_sent": A[A.sequence_step == "enrollment_link"][["lead_id", "activity_at"]],
            "closed_won": A[A.sequence_step == "payment_confirmed"][["lead_id", "activity_at"]],
            "closed_lost": A[(A.activity_type == "note") & A.sequence_step.isin(["closed_lost", "BD6"])][["lead_id", "activity_at"]],
        }
        det, n_omittable = set(), 0
        for name, col in STAGE_TS:
            st = L.loc[L[col].notna(), ["lead_id", col]].rename(columns={col: "activity_at"})
            if name in ("opportunity", "form_completed", "closed_lost"):
                n_omittable += len(st)
            m = st.merge(recs[name].drop_duplicates(), on=["lead_id", "activity_at"], how="left", indicator=True)
            det |= {f"{lid}|{name}" for lid in m.lead_id[m._merge == "left_only"]}
        injected = {f"{a}|{b}" for a, b in G.loc[G.issue_type == "stage_support_omitted", ["lead_id", "detail"]].itertuples(index=False)}
        self.anomaly("stage_support_omitted", "stage timestamp without its dedicated record at the same time", det,
                     injected, rate=len(det) / max(n_omittable, 1), expected=0.04,
                     note="unit = stage event; rate over omittable events (opportunity, form_completed, closed_lost)")

        # governance indicator (looser rule): no activity of the lead within +/-24 h of the stage change
        times = {}
        for lid, g in A.groupby("lead_id"):
            t = list(g.activity_at) + list(g.loc[g.activity_type == "interview", "interview_scheduled_for"].dropna())
            times[lid] = np.sort(np.array(t, dtype="datetime64[s]"))
        loose, n_tr = set(), 0
        win = np.timedelta64(24 * 3600, "s")
        for name, col in STAGE_TS:
            for lid, ts in L.loc[L[col].notna(), ["lead_id", col]].itertuples(index=False):
                n_tr += 1
                arr = times.get(lid, np.array([], dtype="datetime64[s]"))
                x = np.datetime64(ts, "s")
                i = np.searchsorted(arr, x - win)
                if i >= len(arr) or arr[i] > x + win:
                    loose.add(f"{lid}|{name}")
        self.results.append(Result("stage changes with no activity within ±24 h (governance indicator)", "governance",
                                   len(loose), f"{len(loose)} of {n_tr} stage events ({len(loose) / max(n_tr, 1):.1%})",
                                   note=f"stricter view of the same issue: {len(loose)} of the {len(det)} omitted records "
                                        "have no other activity within ±24 h; the rest are covered by nearby activity"))
        self.logic("±24 h indicator is a subset of the omitted support records", sorted(loose - det))

        # stalled: observable only after 30 days without activity
        stall_open = open_ & (L.pipeline_stage.isin(["interview_held", "form_completed"])
                              | ((L.pipeline_stage == "opportunity") & L.first_connected_at.notna()))
        last_act = A[A.activity_type != "task"].groupby("lead_id").activity_at.max()
        idle = set(L.lead_id[L.lead_id.map(last_act) <= self.snap - pd.Timedelta(days=30)])
        det = set(L.lead_id[stall_open]) & idle
        injected = inj("stalled")
        self.anomaly("stalled", "open lead in contacted Opportunity / Interview Held / Form Completed, no activity for 30+ days",
                     det, injected, injected & idle,
                     note="not detectable: last activity < 30 days before the snapshot, indistinguishable from leads in progress")


def cohort_maturity(leads: pd.DataFrame, maturity_days: int = 60) -> pd.DataFrame:
    """Per-lead maturity (snapshot_date - created_at >= N x 24 h, full timestamps) and
    the resulting label of each monthly cohort of eligible leads.

    Madurez por lead con timestamps completos y etiqueta calculada de cada cohorte.
    """
    E = leads[~leads.is_duplicate.astype(bool) & ~leads.is_reactivation.astype(bool)].copy()
    age = E.snapshot_date - E.created_at
    E["mature"] = age >= pd.Timedelta(days=maturity_days)
    E["cohort"] = E.created_at.dt.to_period("M")
    out = E.assign(age=age).groupby("cohort").agg(
        eligible_leads=("lead_id", "size"), mature_leads=("mature", "sum"),
        newest_lead_created_at=("created_at", "max"), min_age=("age", "min"))
    out["mature_share"] = out.mature_leads / out.eligible_leads
    out["label"] = np.select([out.mature_share == 1, out.mature_share == 0], ["mature", "immature"], "partial")
    out["min_age_days"] = (out.pop("min_age").dt.total_seconds() / 86400).round(2)
    return out


def followup_within_48h(leads: pd.DataFrame, acts: pd.DataFrame, hours: int = 48) -> dict:
    """Manual advisor follow-up after the first held interview (project analytical definition).

    Counts an activity only if ALL hold:
      actor_type == "advisor", direction == "outbound", activity_type in {call, whatsapp}, is_automated == False,
      entered_interview_held_at < activity_at <= entered_interview_held_at + 48 h   (calendar hours, weekends included)
    Denominator: eligible leads (no duplicates, no reactivations) whose first held interview satisfies
      entered_interview_held_at + 48 h <= snapshot_date   (window complete before the snapshot).
    Activities before the interview never count, whatever their position in the lead's history.
    """
    snap = leads.snapshot_date.iloc[0]
    win = pd.Timedelta(hours=hours)
    E = leads[~leads.is_duplicate.astype(bool) & ~leads.is_reactivation.astype(bool)]
    H = E[E.entered_interview_held_at.notna() & (E.entered_interview_held_at + win <= snap)][["lead_id", "entered_interview_held_at"]]
    adv = acts[(acts.actor_type == "advisor") & (acts.direction == "outbound")
               & acts.activity_type.isin(["call", "whatsapp"]) & ~acts.is_automated.astype(bool)][["lead_id", "activity_at"]]
    m = adv.merge(H, on="lead_id")
    in_window = (m.activity_at > m.entered_interview_held_at) & (m.activity_at <= m.entered_interview_held_at + win)
    hit = set(m.lead_id[in_window])
    return {"numerator": len(hit), "denominator": len(H),
            "rate": len(hit) / len(H) if len(H) else float("nan"), "leads_with_follow_up": hit}


def run_checks(data_dir: Path = ROOT / "data"):
    leads, acts, gt = load(data_dir)
    ch = Checker(leads, acts, gt)
    table = ch.run()
    return table, ch.warnings


if __name__ == "__main__":
    t, w = run_checks()
    pd.set_option("display.width", 200, "display.max_colwidth", 80, "display.max_rows", 200)
    print(t.to_string())
    print("warnings:", w)
