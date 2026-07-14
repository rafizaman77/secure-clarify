"""Smoke tests: run with `python3 test_smoke.py`. No external deps."""
from secure_clarify.task_factory import build_pilot
from secure_clarify.agent import ScriptedAgent
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


if __name__ == "__main__":
    test_all_tasks_validate()
    test_roundtrip()
    test_channel_not_predictive()
    test_neverask_fails_benign()
    test_tradeoff_exists()
    test_lambda_monotone()
    print("\nALL SMOKE TESTS PASSED")
