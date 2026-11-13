"""Simulation-based power at alpha=.025 (two-sided), assuming independent films.

Z tests: observed group sizes; fix the rotten baseline at its observed rate.
Spearman: continuous Gaussian-copula model, parameterized by population rho_s.
The latter is a model-based approximation, not a recreation of score ties.
"""
from pathlib import Path
import json
import numpy as np
from scipy import stats

ALPHA = .025
rng = np.random.default_rng(20261101)
critical_z = stats.norm.ppf(1 - ALPHA / 2)
results = []

for label, n1, n2, baseline in [
    ('Critic z-test', 998, 1100, 473 / 1100),
    ('Audience z-test', 1253, 845, 340 / 845),
]:
    def power(delta):
        a = rng.binomial(n1, baseline + delta, 100000)
        b = rng.binomial(n2, baseline, 100000)
        pooled = (a + b) / (n1 + n2)
        se = np.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
        return float(np.mean(np.abs((a / n1 - b / n2) / se) > critical_z))

    low, high = 0., .20
    for _ in range(12):
        mid = (low + high) / 2
        if power(mid) >= .80:
            high = mid
        else:
            low = mid
    results.append(dict(test=label, n_fresh=n1, n_rotten=n2,
                        baseline=baseline, mde=high, power_at_mde=power(high),
                        power_at_meaningful_effect=power(.10)))

n, repetitions = 2098, 3000
x = rng.normal(size=(repetitions, n))
noise = rng.normal(size=x.shape)
rank_x = stats.rankdata(x, axis=1) - (n + 1) / 2
rank_ss = n * (n * n - 1) / 12
critical_t = stats.t.ppf(1 - ALPHA / 2, n - 2)

def rank_power(rho_s):
    # For a Gaussian copula, rho_s = 6/pi * arcsin(latent_r / 2).
    latent_r = 2 * np.sin(np.pi * rho_s / 6)
    y = latent_r * x + np.sqrt(1 - latent_r**2) * noise
    rank_y = stats.rankdata(y, axis=1) - (n + 1) / 2
    rho = np.sum(rank_x * rank_y, axis=1) / rank_ss
    t = rho * np.sqrt((n - 2) / (1 - rho**2))
    return float(np.mean(np.abs(t) > critical_t))

low, high = 0., .15
for _ in range(9):
    mid = (low + high) / 2
    if rank_power(mid) >= .80:
        high = mid
    else:
        low = mid
rank_result = dict(n=n, mde=high, power_at_mde=rank_power(high),
                   power_at_meaningful_effect=rank_power(.20),
                   simulations=repetitions)
for label in ['Critic Spearman', 'Audience Spearman']:
    results.append(dict(test=label, **rank_result))

output = dict(alpha=ALPHA, target_power=.80, seed=20261101, results=results)
destination = Path(__file__).parent / 'figures' / 'power_results.json'
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(output, indent=2), encoding='utf-8')
print(json.dumps(output, indent=2))
