"""
TokenShield — Signal 5: Behavioral Biometrics
=============================================
Paper weight: 0.30
Evaluates deviation in keystroke dynamics, typing rhythm, mouse dynamics,
and idle patterns compared against user's established baseline.
Replaces the stub implementation.
"""

import math
import logging
from typing import Tuple, Dict, Any, Optional

from engine.state.user_profiles import UserProfileStore, METRIC_KEYS

log = logging.getLogger("ts.signal5")


class Signal5BehavioralBiometrics:
    def __init__(self, min_samples_warmup: int = 20, anomaly_z_threshold: float = 2.5):
        self.store = UserProfileStore()
        self.min_samples = min_samples_warmup
        self.z_threshold = anomaly_z_threshold

    def evaluate(
        self,
        user_id: Optional[str],
        biometrics: Optional[Dict[str, Any]]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculates anomaly score in [0.0, 1.0].
        0.0 = completely consistent with user baseline or in warm-up phase.
        1.0 = extreme behavioral anomaly (different person using account / hijacking).
        """
        if not user_id or not biometrics:
            return 0.0, {"status": "no_biometrics_provided"}

        profile = self.store.get_profile(str(user_id))

        if not profile or profile.get("sample_count", 0) < self.min_samples:
            # During warm-up, record samples to build baseline
            self.store.update_profile(str(user_id), biometrics)
            sample_count = profile.get("sample_count", 0) + 1 if profile else 1
            return 0.0, {
                "status": "warmup_period",
                "samples_collected": sample_count,
                "samples_required": self.min_samples,
            }

        # Compare against baseline
        z_scores = []
        metrics_eval = {}

        # Sensible minimum variance floors to prevent division by near-zero for constant metrics.
        # Mouse dynamics in particular vary a lot session-to-session (mouse vs trackpad, screen
        # size, task context e.g. typing vs. free cursor movement), so these floors are set wide
        # enough that ordinary variation doesn't read as an anomaly.
        MIN_VAR_FLOOR = {
            "typing_wpm": 25.0,             # std floor of 5 wpm
            "typing_rhythm_cv": 0.0025,     # std floor of 0.05
            "mouse_velocity_mean": 10000.0, # std floor of 100 px/s
            "mouse_velocity_cv": 0.04,      # std floor of 0.2
            "idle_time_ratio": 0.0025       # std floor of 0.05
        }

        for k in METRIC_KEYS:
            if k in biometrics and biometrics[k] is not None:
                val = float(biometrics[k])
                m_stat = profile["metrics"].get(k)
                if m_stat and m_stat.get("count", 0) >= 3:
                    mean = m_stat["mean"]
                    floor_var = MIN_VAR_FLOOR.get(k, 1e-3)
                    var = max(m_stat["variance"], floor_var)
                    std = math.sqrt(var)
                    z = abs(val - mean) / std
                    z_scores.append(z)
                    metrics_eval[k] = {
                        "observed": round(val, 3),
                        "baseline_mean": round(mean, 3),
                        "z_score": round(z, 2),
                    }

        if not z_scores:
            return 0.0, {"status": "insufficient_metrics"}

        # Calculate composite score
        # Using sigmoid-like transformation of maximum & average z-scores
        avg_z = sum(z_scores) / len(z_scores)
        max_z = max(z_scores)

        # Combined metric: 60% max Z, 40% avg Z
        composite_z = 0.6 * max_z + 0.4 * avg_z

        # Map to [0.0, 1.0]: composite_z of 2.5 -> ~0.5; composite_z >= 5 -> ~1.0
        score = 1.0 / (1.0 + math.exp(-1.5 * (composite_z - self.z_threshold)))
        # Zero out small innocent deviations (< 1.5 Z)
        if composite_z < 1.5:
            score = 0.0

        score = float(min(max(score, 0.0), 1.0))

        # Only skip baseline update on a genuinely severe anomaly (prevents baseline poisoning
        # from an actual takeover attempt). Previously this froze the baseline permanently on
        # any score >= 0.6, which meant a single false-positive context shift (e.g. moving the
        # mouse differently right after login) could never self-correct and would keep flagging
        # every subsequent request against the same stale baseline. Raising the cutoff to 0.85
        # lets moderate, legitimate drift continue adapting the baseline.
        if score < 0.85:
            self.store.update_profile(str(user_id), biometrics)

        details = {
            "status": "evaluated",
            "composite_z": round(composite_z, 2),
            "max_z": round(max_z, 2),
            "metrics": metrics_eval,
            "anomaly_detected": score >= 0.7,
        }

        return score, details