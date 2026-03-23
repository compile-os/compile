# Legacy Scripts

Superseded by newer versions or approaches that didn't produce useful results. Kept for completeness.

**Note:** These files have NOT been refactored to use the `compile` library and still contain hardcoded paths. They are preserved for historical reference only.

| Script | Why It's Here |
|--------|--------------|
| `brian2_crossval.py` | v1, superseded by v2. Brian2 cross-validation incomplete (40/50 edges) |
| `brian2_crossval_v2.py` | Brian2 results: 52.5% frozen. Different fitness function than PyTorch — not directly comparable |
| `behavior_manifold.py` | v1, superseded by `behavior_manifold_fast.py` |
| `novel_behaviors.py` | v1, early approach to circles/rhythm compilation |
| `novel_behaviors_v2.py` | Superseded by `bulletproof_evolution.py` with more mutations |
| `dreaming_test.py` | Brain in the dark: 0 spikes. Izhikevich needs initial excitation to fire |
| `dreaming_v2.py` | Noise-seeded dreaming: activity sustained but no behavioral state cycling |
| `gauge_theory_test.py` | GU curvature prediction: p=2.16e-21 but confounded by synapse count |
| `gauge_theory_v2.py` | Partial correlation flipped negative after controlling for synapse count |
| `validate_gauge_theory.py` | Further GU validation — curvature doesn't predict evolvability |
| `replay_test.py` | Early attempt at replaying evolved brains |
| `verify_evolved_brain.py` | Early verification of evolved brain weights |
| `mouse_pipeline_v2.py` | Earlier mouse pipeline, superseded by `mouse_full_pipeline.py` |
