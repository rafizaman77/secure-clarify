"""Smoke tests: run with `python3 test_smoke.py`. No external deps."""
from secure_clarify.task_factory import build_pilot
from secure_clarify.agent import ScriptedAgent, OpenModelAgent
from secure_clarify.policies import NeverAsk, ConventionalVoI, TrustedOnly, SecureVoI
from secure_clarify.runner import run_episode, run_grid, summarize
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
    print("\nALL SMOKE TESTS PASSED")
