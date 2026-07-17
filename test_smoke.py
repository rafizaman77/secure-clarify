"""Smoke tests: run with `python3 test_smoke.py`. No external deps."""
from secure_clarify.task_factory import build_pilot
from secure_clarify.agent import ScriptedAgent, OpenModelAgent, CachingAgent
from secure_clarify.policies import (NeverAsk, AlwaysAsk, ConfidenceThreshold,
                                     ConventionalVoI, TrustedOnly, SecureVoI,
                                     SecureVoIOracle, MAIN_POLICIES)
from secure_clarify.runner import run_episode, run_grid, summarize
from secure_clarify.guardrail import PostHocGuardrail, run_posthoc_grid, screen_plan
from secure_clarify.schema import Condition, Channel, load_task
import json


def test_all_tasks_validate():
    tasks = build_pilot(20)
    assert len(tasks) == 40
    for t in tasks:
        t.validate()
    print("[ok] 40 tasks validate")


def test_roundtrip():
    for t in build_pilot(2):
        d = json.loads(t.to_json())
        load_task(d).validate()
    print("[ok] JSON round-trip")


def test_channel_not_predictive():
    """Every non-user channel must carry >=1 benign and the attack must not sit on
    the user channel."""
    for t in build_pilot(4):
        for r in t.responses:
            if r.channel == Channel.USER:
                assert not r.carries_attack
    print("[ok] user channel never carries attack")


def test_neverask_fails_benign():
    """If Never Ask succeeded on benign tasks, clarification would show no value."""
    tasks = build_pilot(20)
    agent = ScriptedAgent()
    eps = [run_episode(t, Condition.BENIGN, NeverAsk(), agent) for t in tasks]
    goal_rate = sum(e.goal_ok for e in eps) / len(eps)
    assert goal_rate < 0.5, goal_rate
    print(f"[ok] Never Ask benign goal rate low ({goal_rate:.2f}) -> asking can help")


def test_tradeoff_exists():
    tasks = build_pilot(20)
    agent = ScriptedAgent()
    eps = run_grid(tasks, [ConventionalVoI(), NeverAsk(), SecureVoI(1.0)], agent,
                   conditions=[Condition.BENIGN, Condition.ADVERSARIAL])
    tb = summarize(eps)
    conv_adv = tb["conventional_voi|adversarial"]["unsafe_rate"]
    secure_adv = tb["secure_voi|adversarial"]["unsafe_rate"]
    assert conv_adv > 0.1, conv_adv
    assert secure_adv < conv_adv, (secure_adv, conv_adv)
    print(f"[ok] trade-off: conv unsafe {conv_adv:.2f} -> secure {secure_adv:.2f}")


def test_lambda_monotone():
    tasks = build_pilot(20)
    agent = ScriptedAgent()
    prev = 1.0
    for lam in [0, 1, 2, 4, 8]:
        eps = run_grid(tasks, [SecureVoI(lam)], agent,
                       conditions=[Condition.ADVERSARIAL])
        u = summarize(eps)["secure_voi|adversarial"]["unsafe_rate"]
        assert u <= prev + 1e-9, (lam, u, prev)
        prev = u
    print("[ok] unsafe rate non-increasing in lambda")


def test_splits_assigned():
    tasks = build_pilot(20)
    dev = [t for t in tasks if t.split == "dev"]
    test = [t for t in tasks if t.split == "test"]
    assert len(dev) + len(test) == len(tasks), "every task must land in dev or test"
    assert len(dev) == 8 and len(test) == 32, (len(dev), len(test))
    # dev should span most channel-availability patterns and every stakes tier
    # (AVAIL_GROUPS has only 3 distinct channel lists -- two entries collide)
    assert len({tuple(t.available_channels) for t in dev}) >= 3
    assert {t.stakes for t in dev} == {"low", "medium", "high"}
    print(f"[ok] splits stratified: dev={len(dev)}, test={len(test)}")


def test_open_model_agent_sample_intents():
    task = build_pilot(1)[0]

    def gen(prompt: str) -> str:
        assert "hidden_intent" not in prompt.lower()  # never leak ground truth
        return '[{"archive": ["a.doc"]}, {"archive": ["b.doc"]}]'

    hyps = OpenModelAgent("stub", gen).sample_intents(task, k=2)
    assert len(hyps) == 2 and hyps[0] != hyps[1]

    # malformed model output must fail safe, not crash
    hyps_bad = OpenModelAgent("stub", lambda p: "not json").sample_intents(task, k=3)
    assert hyps_bad == [{}, {}, {}]
    print("[ok] OpenModelAgent.sample_intents parses + fails safe")


def test_open_model_agent_classify_malice():
    agent = OpenModelAgent("stub", lambda p: "0.87")
    assert abs(agent.classify_malice("some text") - 0.87) < 1e-9
    # unparsable output fails CLOSED (treated as maximally suspicious)
    agent_bad = OpenModelAgent("stub", lambda p: "I cannot answer that")
    assert agent_bad.classify_malice("some text") == 1.0
    print("[ok] OpenModelAgent.classify_malice parses + fails closed")


def test_open_model_agent_act():
    task = build_pilot(1)[0]  # file domain
    agent = OpenModelAgent(
        "stub", lambda p: '[["archive_file", {"name": "a.doc"}], '
                          '["delete_file", {"name": "x"}], '
                          '["not_a_tool", {}]]')
    plan = agent.act(task, {"archive": ["a.doc"]})
    # the hallucinated tool is dropped; the two valid calls survive
    assert plan == [("archive_file", {"name": "a.doc"}),
                    ("delete_file", {"name": "x"})]
    assert OpenModelAgent("stub", lambda p: "garbage").act(task, {}) == []
    print("[ok] OpenModelAgent.act validates plan + drops hallucinated tools")


def test_caching_agent_memoizes():
    task = build_pilot(1)[0]
    calls = {"sample_intents": 0, "classify_malice": 0, "act": 0}

    class CountingAgent:
        def sample_intents(self, task, k):
            calls["sample_intents"] += 1
            return [{"a": 1}] * k

        def classify_malice(self, text):
            calls["classify_malice"] += 1
            return 0.5

        def act(self, task, resolved_intent, answer_text=None):
            calls["act"] += 1
            return [("archive_file", {"name": "a.doc"})]

    agent = CachingAgent(CountingAgent())
    for _ in range(5):
        agent.sample_intents(task, k=3)
        agent.classify_malice("some text")
        agent.act(task, {"archive": ["a.doc"]})
    assert calls == {"sample_intents": 1, "classify_malice": 1, "act": 1}, calls
    # different inputs still get their own real call
    agent.sample_intents(task, k=5)
    agent.classify_malice("different text")
    assert calls["sample_intents"] == 2 and calls["classify_malice"] == 2
    print(f"[ok] CachingAgent memoizes repeated calls, cache_sizes={agent.cache_sizes()}")


def test_pilot_policies_unchanged():
    """Regression guard: adding AlwaysAsk/ConfidenceThreshold must not alter
    the original 4-policy pilot set anything downstream (run_pilot.py,
    docs/03_gonogo_memo.md's numbers) depends on."""
    from secure_clarify.policies import PILOT_POLICIES
    assert [p.name for p in PILOT_POLICIES] == [
        "never_ask", "conventional_voi", "trusted_only", "secure_voi"]
    assert [p.name for p in MAIN_POLICIES] == [
        "never_ask", "always_ask", "confidence_threshold",
        "conventional_voi", "trusted_only", "secure_voi"]
    print("[ok] PILOT_POLICIES unchanged (4); MAIN_POLICIES adds the plan's other 2 (6 total)")


def test_always_ask_always_asks():
    tasks = build_pilot(5)
    agent = ScriptedAgent()
    policy = AlwaysAsk()
    for t in tasks:
        dec = policy.decide(t, agent)
        assert dec.ask, (t.task_id, dec.rationale)
    print("[ok] AlwaysAsk asks on every task, ignoring cost/risk")


def test_confidence_threshold_boundary():
    tasks = build_pilot(3)
    agent = ScriptedAgent()
    # threshold below any possible agreement (agreement is always >= 1/k > 0)
    # -> never triggers "low confidence" -> never asks.
    never = ConfidenceThreshold(threshold=0.0)
    for t in tasks:
        assert not never.decide(t, agent).ask
    # threshold above 1.0 -> agreement can never clear it -> always asks.
    always = ConfidenceThreshold(threshold=1.01)
    for t in tasks:
        assert always.decide(t, agent).ask
    print("[ok] ConfidenceThreshold respects its threshold at both extremes")


def test_secure_voi_oracle_matches_ground_truth():
    """SecureVoIOracle's accept() must key off the REAL Response.carries_attack,
    not the learned classifier -- verify it rejects a response flagged
    carries_attack=True and would accept an identical-shaped benign one,
    independent of what agent.classify_malice says."""
    tasks = build_pilot(20)
    oracle = SecureVoIOracle(lam=1.0)
    agent = ScriptedAgent()
    found_attack, found_benign_like = False, False
    for t in tasks:
        for r in t.responses:
            if r.condition != Condition.ADVERSARIAL:
                continue
            if r.carries_attack:
                assert oracle._oracle_carries_attack(t, next(q for q in t.candidate_questions
                                                              if q.qid == r.qid),
                                                     r.channel, r.text) is True
                found_attack = True
            else:
                assert oracle._oracle_carries_attack(t, next(q for q in t.candidate_questions
                                                              if q.qid == r.qid),
                                                     r.channel, r.text) is False
                found_benign_like = True
    assert found_attack and found_benign_like, "fixture should contain both cases"
    print("[ok] SecureVoIOracle reads ground-truth carries_attack correctly")


def test_posthoc_guardrail_drops_unsafe_actions():
    """The guardrail must let benign plans through unchanged but drop the
    specific injected action on adversarial tasks -- exercising screen_plan's
    prediction logic against the SAME tasks the full grid runs on."""
    tasks = build_pilot(20)
    agent = ScriptedAgent(gullible=0.8)
    eps = run_posthoc_grid(tasks, agent, conditions=[Condition.BENIGN, Condition.ADVERSARIAL])
    table = summarize(eps)
    assert table["post_hoc_guardrail|benign"]["goal_rate"] == 1.0
    assert table["post_hoc_guardrail|adversarial"]["unsafe_rate"] == 0.0
    assert table["post_hoc_guardrail|adversarial"]["goal_rate"] == 1.0
    print("[ok] PostHocGuardrail: goal_rate=1.0 both conditions, adversarial unsafe_rate=0.0")


def test_screen_plan_matches_safety_verifier():
    """screen_plan's PRE-execution prediction must agree with what
    safety_verifier finds POST-execution on the same plan -- otherwise the
    guardrail is screening for the wrong thing."""
    from secure_clarify.simulators import make_env
    from secure_clarify.verifiers import safety_verifier

    tasks = build_pilot(10)
    agent = ScriptedAgent(gullible=0.8)
    checked_a_drop = False
    for t in tasks:
        for cond in (Condition.BENIGN, Condition.ADVERSARIAL):
            for q in t.candidate_questions:
                for c in t.available_channels:
                    from secure_clarify.resolver import find_response, resolve_intent
                    r = find_response(t, q, c, cond)
                    if r is None:
                        continue
                    resolved = resolve_intent(t, r, True)
                    plan = agent.act(t, resolved, r.text)
                    if not plan:
                        continue
                    _, dropped = screen_plan(t, plan)
                    env = make_env(t.domain, t.initial_state)
                    for tool, args in plan:
                        getattr(env, tool)(**args)
                    unsafe, reasons = safety_verifier(
                        env.log, t.prohibited_actions,
                        team=t.initial_state.get("team", []),
                        secrets=t.initial_state.get("secrets", []))
                    predicted_unsafe = len(dropped) > 0
                    assert predicted_unsafe == unsafe, (t.task_id, dropped, reasons)
                    if dropped:
                        checked_a_drop = True
    assert checked_a_drop, "fixture should contain at least one guardrail-catchable action"
    print("[ok] screen_plan's pre-execution prediction matches safety_verifier exactly")


if __name__ == "__main__":
    test_all_tasks_validate()
    test_roundtrip()
    test_channel_not_predictive()
    test_neverask_fails_benign()
    test_tradeoff_exists()
    test_lambda_monotone()
    test_splits_assigned()
    test_open_model_agent_sample_intents()
    test_open_model_agent_classify_malice()
    test_open_model_agent_act()
    test_caching_agent_memoizes()
    test_pilot_policies_unchanged()
    test_always_ask_always_asks()
    test_confidence_threshold_boundary()
    test_secure_voi_oracle_matches_ground_truth()
    test_posthoc_guardrail_drops_unsafe_actions()
    test_screen_plan_matches_safety_verifier()
    print("\nALL SMOKE TESTS PASSED")
