import sys, json; sys.path.insert(0,'/Users/anaghsangavarapu/Documents/secure_clarify/secure-clarify')
R='/Users/anaghsangavarapu/Documents/secure_clarify/secure-clarify/'
from secure_clarify.schema import Condition, Channel, load_task
from secure_clarify.agent import CachingAgent
from secure_clarify.policies import SecureVoI
from secure_clarify.runner import find_response
from secure_clarify import estimators as E
from scripts.model_backends import build_agent
calib=json.load(open(R+'results/models/mistral-nemo-12b/dev_calibration.json'))
lam=calib['chosen_lambda']; E.set_priors({Channel(c):p for c,p in calib['fitted_channel_priors'].items()})
agent=CachingAgent(build_agent('ollama','mistral-nemo:12b','','','http://localhost:11434'), disk_cache_dir=R+'.cache/agent')
pol=SecureVoI(lam=lam)
tasks=[load_task(d) for d in json.load(open(R+'tasks/main_120.json'))]
out={}
print("REPRODUCING the paper's per-episode audit, per attack tier")
print("  subset = tasks where SecureVoI asks DIRECTLY on the attacked channel\n")
print(f"  {'tier':22s} {'on attacked chan':>17s} {'benign accepted':>16s} {'ATTACK rejected':>16s}")
for cond in (Condition.ADVERSARIAL, Condition.ADVERSARIAL_STEALTH):
    n=ben_acc=adv_rej=0
    for t in tasks:
        d=pol.decide(t,agent)
        if not (d.ask and d.question and d.channel): continue
        r=find_response(t,d.question,d.channel,cond)
        if r is None or not r.carries_attack: continue   # must be ON the attack
        n+=1
        rb=find_response(t,d.question,d.channel,Condition.BENIGN)
        if rb is not None and pol.accept(t,d.question,d.channel,rb.text,agent): ben_acc+=1
        if not pol.accept(t,d.question,d.channel,r.text,agent): adv_rej+=1
    out[cond.value]={"asked_on_attacked_channel":n,"benign_accepted":ben_acc,"attack_rejected":adv_rej,
                     "reject_rate":round(adv_rej/n,4) if n else None}
    print(f"  {cond.value:22s} {n:17d} {ben_acc:>13d}/{n:<2d} {adv_rej:>13d}/{n:<2d}")
json.dump(out, open(R+'results/attacked_channel_audit.json','w'), indent=2)
print(f"\ncache: {agent.disk_stats()}")
