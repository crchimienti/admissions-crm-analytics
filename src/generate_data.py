"""Synthetic data generator — admissions CRM analytics (v1).

Generador de datos sintéticos — analítica CRM de admisiones (v1).

Every row produced here is SYNTHETIC. All probabilities, mixes and timings are
synthetic scenario parameters read from config/simulation_params.yaml; none is a
historical observation. No interventions (personalised WhatsApp, reassignment,
agreed next step) have any programmed causal effect.

Approach
--------
1. Each lead's full lifecycle is simulated as a timeline of events.
2. The timeline is cut at the snapshot: nothing after `snapshot_date` is
   recorded, and the lead's state is derived from the events up to that moment.
3. Duplicates and reactivations are generated as separate rows linked by a
   synthetic `person_key`.
4. Deliberate data-quality anomalies are injected and listed in
   data/dq_ground_truth.csv (a validation aid, not an analytical table).

Usage:  python src/generate_data.py [--config config/simulation_params.yaml] [--out data]
"""
from __future__ import annotations

import argparse
import calendar
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

try:  # allow both `python src/generate_data.py` and `import src.generate_data`
    from calendar_utils import (add_business_days, add_business_hours, at_hour,
                                is_business_day, next_working_time)
except ImportError:  # pragma: no cover
    from src.calendar_utils import (add_business_days, add_business_hours, at_hour,
                                    is_business_day, next_working_time)

ROOT = Path(__file__).resolve().parents[1]

POST_FIELDS = ["candidate_situation", "immediate_interest", "program_interest",
               "decision_maker", "main_objection", "payment_preference", "next_step_agreed"]


# --------------------------------------------------------------------------- #
# Data containers
# --------------------------------------------------------------------------- #
@dataclass
class LeadSim:
    key: int                      # internal id, remapped to lead_id at the end
    person_key: str
    created_at: datetime
    channel: str
    source: str
    profile: str
    program: str
    entry_path: str | None
    first_owner: str
    is_reactivation: bool = False
    is_duplicate: bool = False
    parent_key: int | None = None
    allow_reactivation: bool = True
    # owner history
    reassigned_at: datetime | None = None
    second_owner: str | None = None
    # milestones (full lifecycle, before the snapshot cut)
    opportunity: datetime | None = None
    booked: datetime | None = None
    held: datetime | None = None
    form: datetime | None = None
    link: datetime | None = None
    enrolled: datetime | None = None
    closed_lost: datetime | None = None
    lost_reason: str | None = None
    iloc: list = field(default_factory=list)       # [start, end, end_reason]
    nurture_start: datetime | None = None
    nurture_end: datetime | None = None
    nurture_end_reason: str | None = None
    stall_stage: str | None = None
    stall_time: datetime | None = None
    untouched: bool = False
    post_fields: dict | None = None
    pricing: dict | None = None
    acts: list = field(default_factory=list)
    gt: list = field(default_factory=list)          # (issue_type, detail)

    def owner_at(self, t: datetime) -> str:
        if self.reassigned_at is not None and t >= self.reassigned_at:
            return self.second_owner
        return self.first_owner

    @property
    def terminal(self) -> datetime | None:
        return self.enrolled or self.closed_lost


# --------------------------------------------------------------------------- #
# Generator
# --------------------------------------------------------------------------- #
class Generator:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg["seed"])
        p = cfg["period"]
        self.snapshot = datetime.fromisoformat(p["snapshot"])
        self.last_arrival = self.snapshot - timedelta(minutes=p["last_arrival_buffer_minutes"])
        self.year = datetime.fromisoformat(p["start"]).year
        self.leads: list[LeadSim] = []
        self.pending_reactivations: list[tuple] = []
        self._act_seq = 0
        self._person_seq = 0
        self._lead_seq = 0
        self.advisors = cfg["team"]["advisors"]
        w = cfg["team"]["assignment_weight"]
        self.adv_w = np.array([w[a] for a in self.advisors], dtype=float)
        self.adv_w /= self.adv_w.sum()
        self.channels = list(cfg["channels"].keys())
        cw = np.array([cfg["channels"][c]["weight"] for c in self.channels], dtype=float)
        self.ch_w = cw / cw.sum()

    # ---------------- random helpers ---------------- #
    def u(self, lo, hi):
        return float(self.rng.uniform(lo, hi))

    def bern(self, p):
        return bool(self.rng.random() < p)

    def choice(self, mapping: dict):
        keys = list(mapping.keys())
        probs = np.array([mapping[k] for k in keys], dtype=float)
        return keys[int(self.rng.choice(len(keys), p=probs / probs.sum()))]

    def capped(self, p):
        return min(p, self.cfg["prob_cap"])

    def lognormal_days(self, median, sigma, max_days):
        return float(min(self.rng.lognormal(np.log(median), sigma), max_days))

    def work_time_on(self, d, lo=9.5, hi=18.5):
        return at_hour(d, self.u(lo, hi))

    def new_person(self):
        self._person_seq += 1
        return f"P{self._person_seq:06d}"

    def pick_owner(self, exclude=None):
        if exclude is None:
            return self.advisors[int(self.rng.choice(len(self.advisors), p=self.adv_w))]
        idx = [i for i, a in enumerate(self.advisors) if a != exclude]
        w = self.adv_w[idx] / self.adv_w[idx].sum()
        return self.advisors[idx[int(self.rng.choice(len(idx), p=w))]]

    # ---------------- activity factory ---------------- #
    def act(self, L: LeadSim, t, activity_type, actor_type, direction, *, actor_id=None,
            automated=False, seq="none", step=None, instance=None, bd=None, **extra):
        self._act_seq += 1
        a = dict(_id=self._act_seq, activity_at=t, activity_type=activity_type,
                 actor_type=actor_type, actor_id=actor_id, direction=direction,
                 is_automated=automated, sequence_name=seq, sequence_step=step,
                 sequence_instance=instance, business_day_index=bd)
        if activity_type == "email" and "email_status" not in extra:
            extra["email_status"] = "sent"
        a.update(extra)
        L.acts.append(a)
        return a

    def adv(self, L, t, activity_type, direction="outbound", **kw):
        return self.act(L, t, activity_type, "advisor", direction, actor_id=L.owner_at(t), **kw)

    def call(self, L, t, p_connect, **kw):
        connected = self.bern(p_connect)
        outcome = "connected" if connected else self.choice(self.cfg["contact"]["call_no_connect_outcomes"])
        self.adv(L, t, "call", call_outcome=outcome, **kw)
        return connected

    # ---------------------------------------------------------------- #
    # Lead arrivals
    # ---------------------------------------------------------------- #
    def build_arrivals(self):
        v = self.cfg["volume"]
        hw = np.array(v["hour_weight"], dtype=float)
        hw /= hw.sum()
        lo, hi = v["clip"]
        for month in range(1, 13):
            n = int(np.clip(self.rng.poisson(v["monthly_new_eligible"][month]), lo, hi))
            ndays = calendar.monthrange(self.year, month)[1]
            days = [datetime(self.year, month, d) for d in range(1, ndays + 1)]
            dw = np.array([v["weekday_weight"][d.weekday()] for d in days], dtype=float)
            dw /= dw.sum()
            for _ in range(n):
                while True:
                    d = days[int(self.rng.choice(ndays, p=dw))]
                    t = d + timedelta(hours=int(self.rng.choice(24, p=hw)), seconds=self.u(0, 3600))
                    if t <= self.last_arrival:
                        break
                self.leads.append(self.new_lead(t))
        self.leads.sort(key=lambda L: L.created_at)

    def new_lead(self, t, *, person_key=None, channel=None, source=None, profile=None,
                 program=None, entry_path="auto", is_reactivation=False, parent_key=None):
        cfg = self.cfg
        if channel is None:
            channel = self.channels[int(self.rng.choice(len(self.channels), p=self.ch_w))]
            source = self.rng.choice(cfg["channels"][channel]["sources"]).item()
        if profile is None:
            profile = self.choice(cfg["profiles"]["share"])
            program = self.choice(cfg["profiles"]["program_given_profile"][profile])
        if entry_path == "auto":
            entry_path = "bot_booked" if self.bern(cfg["channels"][channel]["bot_share"]) else "manual"
        self._lead_seq += 1
        return LeadSim(key=self._lead_seq,
                       person_key=person_key or self.new_person(), created_at=t, channel=channel,
                       source=source, profile=profile, program=program, entry_path=entry_path,
                       first_owner=self.pick_owner(), is_reactivation=is_reactivation,
                       parent_key=parent_key, allow_reactivation=not is_reactivation)

    # ---------------------------------------------------------------- #
    # Lifecycle simulation
    # ---------------------------------------------------------------- #
    def mod(self, L):
        return self.cfg["channels"][L.channel]["modifier"]

    def simulate(self, L: LeadSim):
        c = self.cfg
        t0 = L.created_at
        if L.entry_path == "bot_booked":
            tb = t0 + timedelta(minutes=self.u(1, 3))
            sched = self.work_time_on(add_business_days(tb.date(), int(self.rng.integers(
                c["interviews"]["schedule_bd_bot"][0], c["interviews"]["schedule_bd_bot"][1] + 1))))
            self.appointment(L, booker="bot", booked_at=tb, sched=sched, n=1, first_bot=True)
            return
        # manual route: the bot attempts to book, fails, lead goes to Opportunity
        L.opportunity = t0 + timedelta(minutes=self.u(1, 3))
        if self.bern(c["anomalies"]["omit_stage_support_prob"]):
            L.gt.append(("stage_support_omitted", "opportunity"))
        else:
            self.act(L, L.opportunity, "whatsapp", "bot", "outbound", automated=True,
                     seq="booking", step="bot_booking_attempt")
        if self.bern(c["contact"]["untouched_share"]):
            L.untouched = True
            L.gt.append(("untouched_manual", "opportunity"))
            return
        cc = c["contact"]
        delay = float(self.rng.lognormal(np.log(cc["first_attempt_median_business_hours"]), cc["first_attempt_sigma"]))
        planned = add_business_hours(t0, delay)
        check = next_working_time(t0 + timedelta(hours=cc["sla_hours"]))
        attempt = planned
        if planned > check and self.bern(cc["reassignment_prob"]):
            L.reassigned_at = check
            L.second_owner = self.pick_owner(exclude=L.first_owner)
            attempt = add_business_hours(check, self.u(0.1, cc["reassigned_attempt_max_business_hours"]))
        self.contact_sequence(L, attempt, context="initial")

    # ----- ILOC / contact sequence ----------------------------------- #
    def contact_sequence(self, L, t_call, *, context, n=0, noshow_id=None):
        """BD0 call and, if unanswered, the ILOC cadence (BD0..BD5, close BD6)."""
        ic = self.cfg["iloc"]
        f = ic["after_no_show_factor"] if context == "after_no_show" else 1.0
        m = self.mod(L)
        p = lambda base: self.capped(base * f * m)
        bd0 = t_call.date()
        instance = len(L.iloc) + 1

        connected = self.bern(p(ic["p_bd0_call"]))
        first_seq = "first_contact" if context == "initial" else "reschedule"
        outcome = "connected" if connected else self.choice(self.cfg["contact"]["call_no_connect_outcomes"])
        call_row = self.adv(L, t_call, "call", call_outcome=outcome,
                            seq=first_seq if connected else "iloc",
                            step="BD0" if not connected else "first_call",
                            instance=None if connected else instance,
                            bd=None if connected else 0)
        if connected:
            self.after_response(L, t_call, context=context, n=n, noshow_id=noshow_id, iloc_open=False)
            return

        # ILOC activated: WhatsApp + email 1 on BD0
        t_act = t_call + timedelta(minutes=self.u(2, 8))
        L.iloc.append([t_act, None, None])
        self.adv(L, t_act, "whatsapp", seq="iloc", step="BD0", instance=instance, bd=0)
        self.adv(L, t_act + timedelta(minutes=1), "email", automated=True, seq="iloc", step="BD0",
                 instance=instance, bd=0)

        d2, d3, d4, d5, d6 = (add_business_days(bd0, k) for k in (2, 3, 4, 5, 6))
        tasks = {}
        for k, d in ((2, d2), (4, d4)):
            tasks[k] = self.adv(L, t_act + timedelta(minutes=2), "task", direction="internal",
                                seq="iloc", step=f"BD{k}_call_task", instance=instance, bd=k,
                                task_due_at=at_hour(d, 10), _completed=None, _cancelled=None)

        lo, hi = ic["reply_delay_hours"]
        steps = [  # (time, kind, bd, prob, channel)
            (t_act, "reply", 0, p(ic["p_bd0_reply"]), "whatsapp"),
            (self.work_time_on(d2), "call", 2, p(ic["p_bd2_call"]), None),
            (at_hour(d3, self.u(9.0, 10.5)), "email", 3, p(ic["p_bd3_email"]), "email"),
            (self.work_time_on(d4, 9.5, 18.0), "call_wa", 4, None, None),
            (at_hour(d5, self.u(9.0, 10.5)), "email", 5, p(ic["p_bd5_email"]), "email"),
        ]
        response, resp_chan = None, None
        for (t, kind, bd, prob, chan) in steps:
            if response is not None and t >= response:
                break
            if kind == "reply":  # BD0 messages already sent; only the reply is drawn
                if self.bern(prob):
                    response = t + timedelta(hours=self.u(lo, hi))
                    resp_chan = chan
            elif kind == "call":
                ok = self.call(L, t, prob, seq="iloc", step=f"BD{bd}", instance=instance, bd=bd)
                tasks[bd]["_completed"] = t
                if ok:
                    response, resp_chan = t, None
            elif kind == "email":
                self.adv(L, t, "email", automated=True, seq="iloc", step=f"BD{bd}", instance=instance, bd=bd)
                if self.bern(prob):
                    response, resp_chan = t + timedelta(hours=self.u(lo, hi)), "email"
            elif kind == "call_wa":
                ok = self.call(L, t, p(ic["p_bd4_call"]), seq="iloc", step="BD4", instance=instance, bd=4)
                tasks[4]["_completed"] = t
                if ok:
                    response, resp_chan = t, None
                else:
                    tw = t + timedelta(minutes=self.u(2, 8))
                    self.adv(L, tw, "whatsapp", seq="iloc", step="BD4", instance=instance, bd=4)
                    if self.bern(p(ic["p_bd4_whatsapp"])):
                        response, resp_chan = tw + timedelta(hours=self.u(lo, hi)), "whatsapp"

        for k, tk in tasks.items():
            if tk["_completed"] is None and response is not None:
                tk["_cancelled"] = response

        if response is None:  # ILOC closure on BD6
            t_close = at_hour(d6, self.u(9.0, 11.0))
            L.iloc[-1][1:] = [t_close, "closed_iloc"]
            self.close(L, t_close, "iloc", note_seq="iloc", note_step="BD6", instance=instance, bd=6)
            return
        if resp_chan is not None:  # inbound reply from the candidate
            self.act(L, response, resp_chan, "candidate", "inbound", seq="iloc", step="reply",
                     instance=instance)
        self.after_response(L, response, context=context, n=n, noshow_id=noshow_id, iloc_open=True)

    def after_response(self, L, t, *, context, n, noshow_id, iloc_open):
        c = self.cfg
        maxn = c["interviews"]["max_appointments"]
        if context == "initial":
            book = self.bern(self.capped(c["booking"]["p_book_after_contact"] * self.mod(L)))
        else:
            book = n < maxn and self.bern(c["interviews"]["rebook_after_iloc_response_prob"])
        if iloc_open:
            L.iloc[-1][1:] = [t, "booked" if book else "responded"]
        if book:
            tb = t + timedelta(minutes=self.u(2, 10))
            lo, hi = c["interviews"]["schedule_bd_manual"]
            sched = self.work_time_on(add_business_days(tb.date(), int(self.rng.integers(lo, hi + 1))))
            self.appointment(L, booker="advisor", booked_at=tb, sched=sched, n=n + 1,
                             rebooked_after=noshow_id)
            return
        if context == "initial":
            st = c["anomalies"]["stall"]["contacted_opportunity"] * (
                c["anomalies"]["stall"]["september_factor"] if t.month == 9 else 1)
            if self.bern(st):
                L.stall_stage, L.stall_time = "opportunity", t
                return
        k = int(self.rng.integers(c["booking"]["contacted_no_booking_close_bd"][0],
                                  c["booking"]["contacted_no_booking_close_bd"][1] + 1))
        t_close = max(next_working_time(t), self.work_time_on(add_business_days(t.date(), k)))
        if t_close <= t:
            t_close = next_working_time(t + timedelta(minutes=30))
        self.close(L, t_close, self.choice(c["booking"]["lost_mix_contacted_no_booking"]))

    # ----- appointments ---------------------------------------------- #
    def appointment(self, L, *, booker, booked_at, sched, n, first_bot=False,
                    rebooked_after=None, rescheduled_from=None):
        c = self.cfg["interviews"]
        if L.booked is None:
            L.booked = booked_at
        row = self.act(L, booked_at, "interview", booker,
                       "internal", actor_id=L.owner_at(booked_at) if booker == "advisor" else None,
                       automated=(booker == "bot"), seq="booking",
                       step="bot_booking" if booker == "bot" else "advisor_booking",
                       interview_scheduled_for=sched, interviewer_id=L.owner_at(sched),
                       rescheduled_from=rescheduled_from, rebooked_after=rebooked_after,
                       replaced_by=None, _outcome=None, _outcome_time=None)
        # confirmations & reminders (no causal effect on the outcome)
        if booker == "bot" and self.bern(c["bot_confirmation_prob"]):
            self.act(L, booked_at + timedelta(minutes=1), "whatsapp", "bot", "outbound",
                     automated=True, seq="pre_interview_reminder", step="bot_confirmation")
        if self.bern(c["reminder_24h_prob"]):
            tr = max(sched - timedelta(hours=24), booked_at + timedelta(minutes=15))
            self.act(L, tr, "email", "bot", "outbound", automated=True,
                     seq="pre_interview_reminder", step="reminder_24h")
        if sched >= datetime.fromisoformat(c["personal_whatsapp_start"]) and self.bern(c["personal_whatsapp_prob"]):
            prev = sched.date() - timedelta(days=1)
            while not is_business_day(prev):
                prev -= timedelta(days=1)
            tw = self.work_time_on(prev, 10.0, 18.5)
            if tw > booked_at:
                self.adv(L, tw, "whatsapp", seq="pre_interview_reminder", step="personal_whatsapp")
        if first_bot and self.bern(c["bot_route_human_contact_prob"]):
            tc = add_business_hours(booked_at, self.u(1, 20))
            if tc < sched - timedelta(hours=1):
                self.call(L, tc, c["bot_route_human_call_connect_prob"],
                          seq="pre_interview_reminder", step="advisor_pre_interview_call")

        probs = dict(c["outcome_probs"]["bot_booked" if L.entry_path == "bot_booked" else "manual"])
        if n >= c["max_appointments"]:
            probs.pop("rescheduled")
        outcome = self.choice(probs)
        row["_outcome"] = outcome
        lo_n, hi_n = c["change_notice_hours"]

        if outcome == "held":
            row["_outcome_time"] = sched
            if L.held is None:
                L.held = sched
            self.post_interview(L, sched)
        elif outcome == "no_show":
            t_ns = sched + timedelta(minutes=15)
            row["_outcome_time"] = t_ns
            self.act(L, t_ns + timedelta(minutes=self.u(10, 40)), "whatsapp", "bot", "outbound",
                     automated=True, seq="reschedule", step="bot_reschedule_attempt")
            if n < c["max_appointments"] and self.bern(c["rebook_after_no_show_prob"]):
                k = int(self.rng.integers(c["rebook_after_no_show_bd"][0], c["rebook_after_no_show_bd"][1] + 1))
                tb = max(t_ns + timedelta(hours=1), at_hour(add_business_days(t_ns.date(), k), self.u(9, 21)))
                lo, hi = c["replacement_schedule_bd"]
                s2 = self.work_time_on(add_business_days(tb.date(), int(self.rng.integers(lo, hi + 1))))
                self.appointment(L, booker="bot", booked_at=tb, sched=s2, n=n + 1, rebooked_after=row["_id"])
            else:
                bd0 = add_business_days(t_ns.date(), self.cfg["iloc"]["after_no_show_start_bd"])
                self.contact_sequence(L, self.work_time_on(bd0), context="after_no_show", n=n,
                                      noshow_id=row["_id"])
        elif outcome == "rescheduled":
            t_r = max(sched - timedelta(hours=self.u(lo_n, hi_n)), booked_at + timedelta(minutes=5))
            row["_outcome_time"] = t_r
            lo, hi = c["replacement_schedule_bd"]
            s2 = self.work_time_on(add_business_days(sched.date(), int(self.rng.integers(lo, hi + 1))))
            who = "bot" if self.bern(0.5) else "advisor"
            child = self.appointment(L, booker=who, booked_at=t_r, sched=s2, n=n + 1,
                                     rescheduled_from=row["_id"])
            row["replaced_by"] = child["_id"]
        else:  # cancelled
            t_c = max(sched - timedelta(hours=self.u(lo_n, hi_n)), booked_at + timedelta(minutes=5))
            row["_outcome_time"] = t_c
            if n < c["max_appointments"] and self.bern(c["rebook_after_cancel_prob"]):
                tb = max(next_working_time(t_c + timedelta(minutes=30)),
                         self.work_time_on(add_business_days(t_c.date(), int(self.rng.integers(0, 3)))))
                lo, hi = c["replacement_schedule_bd"]
                s2 = self.work_time_on(add_business_days(tb.date(), int(self.rng.integers(lo, hi + 1))))
                self.appointment(L, booker="advisor", booked_at=tb, sched=s2, n=n + 1, rebooked_after=row["_id"])
            else:
                k = int(self.rng.integers(0, 4))
                t_close = max(next_working_time(t_c + timedelta(minutes=30)),
                              self.work_time_on(add_business_days(t_c.date(), k)))
                self.close(L, t_close, self.choice(self.cfg["booking"]["lost_mix_contacted_no_booking"]))
        return row

    # ----- post-interview -------------------------------------------- #
    def post_interview(self, L, th):
        c = self.cfg["post_interview"]
        an = self.cfg["anomalies"]
        m = self.mod(L)
        # outcome path (drawn first so post-interview fields can be coherent with it)
        stall_held = self.bern(an["stall"]["interview_held"] * (an["stall"]["september_factor"] if th.month == 9 else 1))
        p_form = self.capped(c["p_form"] * m * self.cfg["profiles"]["form_modifier"][L.profile])
        has_form = (not stall_held) and self.bern(p_form)

        d_post = self.u(0.5, 23.5) if self.bern(c["post_email_within_24h_prob"]) else self.u(24, 72)
        self.adv(L, th + timedelta(hours=d_post), "email", automated=True, seq="post_interview",
                 step="proposal_email")
        target = th + timedelta(hours=self.u(2, 46) if self.bern(c["advisor_followup_within_48h_prob"])
                                else self.u(50, 120))
        tf = next_working_time(target)
        if self.bern(0.5):
            self.call(L, tf, 0.6, seq="post_interview", step="advisor_follow_up")
        else:
            self.adv(L, tf, "whatsapp", seq="post_interview", step="advisor_follow_up")

        t_form = None
        if has_form:
            t_form = th + timedelta(days=self.lognormal_days(c["form_days_median"], c["timing_sigma"], c["form_days_max"]))
        for h in (24, 48):
            tr = th + timedelta(hours=h)
            if t_form is None or t_form > tr:
                self.act(L, tr, "whatsapp", "bot", "outbound", automated=True, seq="form_reminder",
                         step=f"form_reminder_{h}h")

        if stall_held:
            L.stall_stage, L.stall_time = "interview_held", th
            self.set_post_fields(L, None, None)
            return
        if not has_form:
            t_close = next_working_time(th + timedelta(days=self.u(*c["close_no_form_days"])))
            reason = self.choice(c["lost_mix_no_form"])
            self.set_post_fields(L, reason, None)
            self.close(L, t_close, reason)
            return

        L.form = t_form
        if self.bern(an["omit_stage_support_prob"]):
            L.gt.append(("stage_support_omitted", "form_completed"))
        else:
            self.act(L, t_form, "note", "system", "internal", automated=True, seq="form", step="form_received")
        self.adv(L, next_working_time(t_form + timedelta(hours=self.u(1, 20))), "call",
                 call_outcome="connected", seq="form", step="form_follow_up")
        if self.bern(an["stall"]["form_completed"] * (an["stall"]["september_factor"] if t_form.month == 9 else 1)):
            L.stall_stage, L.stall_time = "form_completed", t_form
            self.set_post_fields(L, None, None)
            return
        if not self.bern(c["p_link"]):
            t_close = next_working_time(t_form + timedelta(days=self.u(*c["close_no_link_days"])))
            reason = self.choice(c["lost_mix_no_link"])
            self.set_post_fields(L, reason, None)
            self.close(L, t_close, reason)
            return
        L.link = next_working_time(t_form + timedelta(days=self.lognormal_days(
            c["link_days_median"], c["timing_sigma"], c["link_days_max"])))
        self.adv(L, L.link, "email", automated=True, seq="enrollment", step="enrollment_link")
        if not self.bern(self.capped(c["p_enroll"] * m)):
            t_close = next_working_time(L.link + timedelta(days=self.u(*c["close_no_enroll_days"])))
            reason = self.choice(c["lost_mix_no_enroll"])
            self.set_post_fields(L, reason, None)
            self.close(L, t_close, reason)
            return
        L.enrolled = L.link + timedelta(days=self.lognormal_days(
            c["enroll_days_median"], c["timing_sigma"], c["enroll_days_max"]))
        self.act(L, L.enrolled, "note", "system", "internal", automated=True, seq="enrollment",
                 step="payment_confirmed")
        self.act(L, L.enrolled + timedelta(minutes=self.u(2, 15)), "email", "system", "outbound",
                 automated=True, seq="enrollment", step="enrollment_confirmation")
        self.set_post_fields(L, None, "won")
        self.set_pricing(L)

    def set_post_fields(self, L, lost_reason, outcome):
        f = self.cfg["post_interview_fields"]
        pc = self.cfg["post_interview"]
        if lost_reason == "financial" and self.bern(pc["objection_match_prob"]):
            obj = "price"
        elif lost_reason == "official_qualification" and self.bern(pc["objection_match_prob"]):
            obj = "official_qualification"
        else:
            obj = self.choice(f["main_objection_base"])
        L.post_fields = dict(
            candidate_situation=self.choice(f["candidate_situation"]),
            immediate_interest=self.choice(f["immediate_interest"]),
            program_interest=self.choice(f["program_interest"]),
            decision_maker=self.choice(f["decision_maker"]),
            main_objection=obj,
            payment_preference=None,  # set below
            next_step_agreed=self.bern(pc["next_step_agreed_prob"]),
        )

    def set_pricing(self, L):
        pr = self.cfg["pricing"]
        f = self.cfg["post_interview_fields"]
        p_inst = pr["installments_prob_if_price_objection"] if L.post_fields["main_objection"] == "price" \
            else pr["installments_prob"]
        ptype = "installments" if self.bern(p_inst) else "single"
        disc = int(self.choice({int(k): v for k, v in pr["campaign_discount_probs"].items()}))
        lst = float(pr["list_price"])
        one = round((lst - disc) * pr["one_time_extra_discount"], 2) if ptype == "single" else 0.0
        L.pricing = dict(payment_type=ptype, list_price=lst, campaign_discount=float(disc),
                         one_time_discount=one, net_price=round(lst - disc - one, 2))

    # ----- closing & nurture ----------------------------------------- #
    def close(self, L, t, reason, *, note_seq="none", note_step="closed_lost", instance=None, bd=None):
        L.closed_lost, L.lost_reason = t, reason
        if self.bern(self.cfg["anomalies"]["omit_stage_support_prob"]):
            L.gt.append(("stage_support_omitted", "closed_lost"))
        else:
            self.adv(L, t, "note", direction="internal", seq=note_seq, step=note_step,
                     instance=instance, bd=bd)
        if reason != "future_intake":
            return
        n = self.cfg["nurture"]
        if not self.bern(n["enter_prob"]):
            return
        L.nurture_start = t
        end = t + timedelta(days=n["window_days"])
        end_reason = "window_ended"
        if L.allow_reactivation and self.bern(n["reactivation_prob"]):
            end = t + timedelta(days=self.u(*n["reactivation_days"]))
            if self.last_arrival < end <= self.snapshot:   # no lead can be created in the final buffer
                end = self.snapshot + timedelta(hours=1)
            end_reason = "reactivated"
            self.pending_reactivations.append((L, end))
        L.nurture_end, L.nurture_end_reason = end, end_reason
        for i, dday in enumerate(n["emails_at_days"], start=1):
            te = at_hour((t + timedelta(days=dday + self.u(-n["email_jitter_days"], n["email_jitter_days"]))).date(),
                         self.u(9, 11))
            if te < end:
                self.act(L, te, "email", "bot", "outbound", automated=True, seq="nurture",
                         step=f"nurture_email_{i}", email_status=self.choice(n["email_status_probs"]))

    # ---------------------------------------------------------------- #
    # Orchestration
    # ---------------------------------------------------------------- #
    def run(self):
        self.build_arrivals()
        n_new = len(self.leads)
        for L in list(self.leads):
            self.simulate(L)
        # reactivations (processed in creation order; they cannot reactivate again)
        react = []
        self.pending_reactivations.sort(key=lambda x: x[1])
        for parent, t in self.pending_reactivations:
            if t > self.last_arrival:
                continue  # after the snapshot: not recorded
            R = self.new_lead(t, person_key=parent.person_key, channel=parent.channel, source=parent.source,
                              profile=parent.profile, program=parent.program, entry_path="manual",
                              is_reactivation=True, parent_key=parent.key)
            self.simulate(R)
            react.append(R)
        # duplicates (additional on top of new eligible leads)
        an = self.cfg["anomalies"]
        n_dup = int(round(an["duplicate_share"] * n_new))
        originals = [L for L in self.leads if not L.is_reactivation
                     and (self.last_arrival - L.created_at).total_seconds() > 0.01 * 86400]
        idx = self.rng.choice(len(originals), size=n_dup, replace=False)
        dups = []
        for i in sorted(idx):
            O = originals[int(i)]
            max_d = min(an["duplicate_max_days"], (self.last_arrival - O.created_at).total_seconds() / 86400)
            t = O.created_at + timedelta(days=self.u(0.001, max_d))
            if self.bern(0.5):
                ch, src = O.channel, O.source
            else:
                ch = self.channels[int(self.rng.choice(len(self.channels), p=self.ch_w))]
                src = self.rng.choice(self.cfg["channels"][ch]["sources"]).item()
            D = LeadSim(key=-(len(dups) + 1), person_key=O.person_key, created_at=t, channel=ch, source=src,
                        profile=O.profile, program=O.program, entry_path=None,
                        first_owner=self.pick_owner(), is_duplicate=True, allow_reactivation=False)
            D.gt.append(("duplicate", "new_lead"))
            dups.append(D)
        self.all = self.leads + react + dups
        return self.snapshot_tables()

    # ---------------------------------------------------------------- #
    # Snapshot cut
    # ---------------------------------------------------------------- #
    def snapshot_tables(self):
        snap = self.snapshot
        an = self.cfg["anomalies"]
        # stable ids by creation order
        self.all.sort(key=lambda L: (L.created_at, L.person_key))
        key2id = {L.key: f"L{i:06d}" for i, L in enumerate(self.all, start=1)}
        lead_rows, act_rows, gt_rows = [], [], []

        for L in self.all:
            lid = key2id[L.key]
            ok = lambda t: t is not None and t <= snap
            v = lambda t: t if ok(t) else None
            term = L.terminal
            # ---- activities up to the snapshot ----
            acts = []
            for a in L.acts:
                t = a["activity_at"]
                if t > snap:
                    continue
                if term is not None and t > term + timedelta(hours=1) and a["sequence_name"] != "nurture":
                    continue  # nothing but nurture after the deal is closed
                acts.append(dict(a))
            for a in acts:
                if a["activity_type"] == "interview":
                    ot = a.pop("_outcome_time")
                    o = a.pop("_outcome")
                    a["interview_outcome"] = o if ot is not None and ot <= snap else "pending"
                    if a["interview_outcome"] != "rescheduled":
                        a["replaced_by"] = None
                if a["activity_type"] == "task":
                    comp, canc = a.pop("_completed"), a.pop("_cancelled")
                    if ok(comp):
                        a["task_status"], a["task_completed_at"] = "done", comp
                    elif ok(canc):
                        a["task_status"], a["task_completed_at"] = "cancelled", None
                    else:
                        a["task_status"] = "overdue" if a["task_due_at"] < snap else "open"
                        a["task_completed_at"] = None
            # ---- milestones ----
            enrolled, closed = v(L.enrolled), v(L.closed_lost)
            stage_times = [("new_lead", L.created_at), ("opportunity", v(L.opportunity)),
                           ("interview_booked", v(L.booked)), ("interview_held", v(L.held)),
                           ("form_completed", v(L.form)), ("enrollment_link_sent", v(L.link))]
            stage = [s for s, t in stage_times if t is not None][-1]
            if enrolled:
                stage = "closed_won"
            elif closed:
                stage = "closed_lost"
            is_open = stage not in ("closed_won", "closed_lost")

            # ILOC: latest episode started by the snapshot
            eps = [e for e in L.iloc if e[0] <= snap]
            il_start = il_end = il_reason = None
            if eps:
                il_start = eps[-1][0]
                if eps[-1][1] is not None and eps[-1][1] <= snap:
                    il_end, il_reason = eps[-1][1], eps[-1][2]
            # nurture
            n_start = v(L.nurture_start)
            n_end = v(L.nurture_end) if n_start else None
            n_reason = L.nurture_end_reason if n_end else None

            # derived contact fields
            adv_out = [a["activity_at"] for a in acts if a["actor_type"] == "advisor" and a["direction"] == "outbound"
                       and a["activity_type"] in ("call", "whatsapp") and not a["is_automated"]]
            first_attempt = min(adv_out) if adv_out else None
            conn = [a["activity_at"] for a in acts if (a["activity_type"] == "call" and a.get("call_outcome") == "connected")
                    or a["direction"] == "inbound"]
            conn += [a["interview_scheduled_for"] for a in acts
                     if a["activity_type"] == "interview" and a["interview_outcome"] == "held"]
            first_conn = min(conn) if conn else None

            # status
            if L.is_duplicate:
                status = "new"
            elif stage == "closed_won":
                status = "closed_won"
            elif stage == "closed_lost":
                status = "nurture" if (n_start and n_end is None) else "closed_lost"
            elif il_start is not None and il_end is None:
                status = "iloc_sequence"
            elif L.entry_path == "manual" and first_attempt is None:
                status = "new"
            else:
                status = "working"

            stalled = L.stall_time is not None and L.stall_time <= snap and is_open
            if stalled:
                gt_rows.append((lid, "stalled", L.stall_stage))
            stage_at = {"opportunity": L.opportunity, "form_completed": L.form, "closed_lost": L.closed_lost}
            for issue, detail in L.gt:
                if issue == "untouched_manual" and not is_open:
                    continue
                if issue == "stage_support_omitted" and not ok(stage_at[detail]):
                    continue
                gt_rows.append((lid, issue, detail))

            # ---- next task for open leads (governance) ----
            if is_open and not L.is_duplicate:
                natural = [a for a in acts if a["activity_type"] == "task" and a["task_status"] in ("open", "overdue")]
                if not natural:
                    last = max(a["activity_at"] for a in acts) if acts else L.created_at
                    if self.bern(an["open_without_task_share"]):
                        gt_rows.append((lid, "open_without_task", stage))
                    else:
                        if stalled:
                            due = at_hour(add_business_days(last.date(), int(self.rng.integers(1, 4))), 10)
                        elif (snap - last).total_seconds() > 600 and self.bern(an["overdue_task_share"]):
                            due = last + timedelta(seconds=self.u(60, (snap - last).total_seconds() - 120))
                        else:
                            due = at_hour(add_business_days(snap.date(), int(self.rng.integers(1, 4))), 10)
                        self._act_seq += 1
                        acts.append(dict(_id=self._act_seq, activity_at=last, activity_type="task",
                                         actor_type="advisor", actor_id=L.owner_at(last), direction="internal",
                                         is_automated=False, sequence_name="none", sequence_step="next_step",
                                         sequence_instance=None, business_day_index=None, task_due_at=due,
                                         task_completed_at=None,
                                         task_status="overdue" if due < snap else "open"))
                        if due < snap:  # ground truth = leads whose injected follow-up task is overdue
                            gt_rows.append((lid, "overdue_task", "stalled_lead" if stalled else "injected"))
            open_tasks = [a for a in acts if a["activity_type"] == "task" and a["task_status"] in ("open", "overdue")]

            # ---- interviews summary ----
            itv = sorted([a for a in acts if a["activity_type"] == "interview"], key=lambda a: a["activity_at"])
            non_rep = [a for a in itv if a["replaced_by"] is None]
            last_outcome = non_rep[-1]["interview_outcome"] if non_rep else None

            held_ok = ok(L.held)
            pf = dict(L.post_fields) if (held_ok and L.post_fields) else {k: None for k in POST_FIELDS}
            pricing = L.pricing if enrolled else None
            if held_ok and L.post_fields:
                pref_src = pricing["payment_type"] if pricing else None
                if pref_src and self.bern(self.cfg["post_interview_fields"]["payment_preference_match_prob"]):
                    pf["payment_preference"] = pref_src
                else:
                    pf["payment_preference"] = self.choice({"single": 0.4, "installments": 0.4, "undecided": 0.2})

            reassigned = L.reassigned_at is not None and L.reassigned_at <= snap
            row = dict(
                lead_id=lid, person_key=L.person_key, is_reactivation=L.is_reactivation,
                reactivated_from_lead_id=key2id.get(L.parent_key) if L.parent_key is not None else None,
                is_duplicate=L.is_duplicate, is_synthetic=True, created_at=L.created_at,
                source=L.source, channel_group=L.channel, program_alias=L.program, candidate_profile=L.profile,
                entry_path=L.entry_path, first_owner_id=L.first_owner,
                current_owner_id=L.second_owner if reassigned else L.first_owner,
                reassigned_flag=reassigned, reassigned_at=L.reassigned_at if reassigned else None,
                first_human_attempt_at=first_attempt, first_connected_at=first_conn,
                entered_opportunity_at=v(L.opportunity), entered_interview_booked_at=v(L.booked),
                entered_interview_held_at=v(L.held), entered_form_completed_at=v(L.form),
                entered_enrollment_link_sent_at=v(L.link), enrolled_at=enrolled, closed_lost_at=closed,
                pipeline_stage=stage, lead_status=status, last_interview_outcome=last_outcome,
                lost_reason=L.lost_reason if closed else None,
                iloc_started_at=il_start, iloc_ended_at=il_end, iloc_end_reason=il_reason,
                iloc_episode_count=len(eps),
                nurture_started_at=n_start, nurture_ended_at=n_end, nurture_end_reason=n_reason,
                has_open_task=bool(open_tasks),
                next_task_due_at=min(a["task_due_at"] for a in open_tasks) if open_tasks else None,
                **pf,
                payment_type=pricing["payment_type"] if pricing else None,
                list_price=pricing["list_price"] if pricing else None,
                campaign_discount=pricing["campaign_discount"] if pricing else None,
                one_time_discount=pricing["one_time_discount"] if pricing else None,
                net_price=pricing["net_price"] if pricing else None,
                snapshot_date=snap,
            )
            if L.is_duplicate:  # duplicates: identity + routing only, no lifecycle
                for k in ("entry_path", "first_human_attempt_at", "first_connected_at"):
                    row[k] = None
            lead_rows.append(row)
            for a in acts:
                a["lead_id"] = lid
                act_rows.append(a)

        leads = pd.DataFrame(lead_rows)
        # ---- post-snapshot anomalies on lead fields ----
        lost_pool = leads[(leads.pipeline_stage == "closed_lost") & (leads.lead_status == "closed_lost")
                          & (leads.lost_reason != "iloc") & leads.nurture_started_at.isna()].index
        n_missing = min(len(lost_pool), int(round(an["missing_lost_reason_share"] * (leads.pipeline_stage == "closed_lost").sum())))
        for i in self.rng.choice(lost_pool, size=n_missing, replace=False):
            gt_rows.append((leads.at[i, "lead_id"], "missing_lost_reason", leads.at[i, "lost_reason"]))
            leads.at[i, "lost_reason"] = None
        held_pool = leads[leads.entered_interview_held_at.notna() & ~leads.is_duplicate].index
        n_empty = int(round(an["empty_post_interview_share"] * len(held_pool)))
        for i in self.rng.choice(held_pool, size=n_empty, replace=False):
            k = int(self.rng.integers(1, 4))
            cols = list(self.rng.choice(POST_FIELDS, size=k, replace=False))
            for col in cols:
                leads.at[i, col] = None
            gt_rows.append((leads.at[i, "lead_id"], "empty_post_interview_fields", ";".join(sorted(cols))))

        acts = pd.DataFrame(act_rows)
        acts = acts.sort_values(["activity_at", "_id"]).reset_index(drop=True)
        id_map = {old: f"A{i:07d}" for i, old in enumerate(acts["_id"], start=1)}
        acts["activity_id"] = acts["_id"].map(id_map)
        for col_src, col_dst in (("rescheduled_from", "rescheduled_from_activity_id"),
                                 ("replaced_by", "replaced_by_activity_id"),
                                 ("rebooked_after", "rebooked_after_activity_id")):
            acts[col_dst] = acts[col_src].map(lambda x: id_map.get(x) if pd.notna(x) else None)
        act_cols = ["activity_id", "lead_id", "activity_at", "actor_type", "actor_id", "activity_type",
                    "direction", "is_automated", "sequence_name", "sequence_step", "sequence_instance",
                    "business_day_index", "call_outcome", "email_status", "interview_scheduled_for",
                    "interview_outcome", "interviewer_id", "rescheduled_from_activity_id",
                    "replaced_by_activity_id", "rebooked_after_activity_id", "task_due_at",
                    "task_completed_at", "task_status"]
        acts = acts[act_cols]
        gt = pd.DataFrame(gt_rows, columns=["lead_id", "issue_type", "detail"]).sort_values(
            ["lead_id", "issue_type"]).reset_index(drop=True)
        return leads, acts, gt


# --------------------------------------------------------------------------- #
def _fmt(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if c.endswith("_at") or c in ("interview_scheduled_for", "snapshot_date"):
            out[c] = pd.to_datetime(out[c]).dt.floor("s")
    for c in ("sequence_instance", "business_day_index"):
        if c in out.columns:
            out[c] = out[c].astype("Int64")
    return out


def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def generate(config_path: Path = ROOT / "config" / "simulation_params.yaml"):
    cfg = load_config(config_path)
    leads, acts, gt = Generator(cfg).run()
    return _fmt(leads), _fmt(acts), gt


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default=str(ROOT / "config" / "simulation_params.yaml"))
    ap.add_argument("--out", default=str(ROOT / "data"))
    args = ap.parse_args()
    leads, acts, gt = generate(Path(args.config))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    leads.to_csv(out / "leads.csv", index=False, lineterminator="\n")
    acts.to_csv(out / "activities.csv", index=False, lineterminator="\n")
    gt.to_csv(out / "dq_ground_truth.csv", index=False, lineterminator="\n")
    print(f"leads: {len(leads):,}  activities: {len(acts):,}  dq_ground_truth: {len(gt):,}  -> {out}")


if __name__ == "__main__":
    main()
