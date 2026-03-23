<p align="center">
  <img src="latent/frontend/public/brand/logomark-512.png" width="80" alt="Compile" />
</p>

<h1 align="center">Compile</h1>

<p align="center">
We design biological brains. Specify behaviors, select an architecture, compile a neural circuit, grow it from a developmental recipe.
</p>

<p align="center">
  <a href="https://compile.now">Website</a> · <a href="https://compile.now/research">Research</a> · <a href="https://compile.now/docs">Docs</a> · <a href="https://compile.now/playground">Playground</a> · <a href="https://github.com/compile-os">GitHub</a>
</p>

---

## What it does

Compile is a platform for designing biological neural circuits to specification. Describe what a brain should do. The system designs the architecture, compiles behaviors onto it through directed evolution, and outputs a developmental growth program — the recipe a stem cell lab needs to grow the circuit.

26 neural architectures tested across 5 behavioral tasks. Composites validated to 28,000 neurons across 10 regions. Minimum viable circuit: 3,000 neurons. All results computational — wet lab validation is next.

## Quick start

```bash
cd latent/ml
pip install -e ".[dev]"
make test          # no data needed
make reproduce-core  # needs FlyWire data
```

### Full stack (Docker)

```bash
cd latent/infrastructure/docker
docker compose up -d
# Frontend: localhost:3000
# API: localhost:8080
# Worker: localhost:8000
```

### Data

Download FlyWire v783 connectome data from [flywire.ai](https://flywire.ai). See [`latent/ml/DATA.md`](latent/ml/DATA.md) for details.

## The pipeline

```
Specify behaviors → Design architecture → Compile → Validate → Growth program → Grow → Build in tissue
```

1. **Specify** — describe behaviors as fitness functions (navigation, working memory, conflict resolution, etc.)
2. **Architecture** — choose from 26 tested architectures or let the system recommend based on computational requirements
3. **Compile** — generate a connectome from the architecture spec, run directed evolution to find wiring changes
4. **Validate** — interference testing, persistence classification, cross-architecture comparison
5. **Growth program** — reverse-compile to a developmental recipe: cell types, proportions, connection rules, growth order
6. **Grow** — sequential activity-dependent growth produces functional circuits from specification alone
7. **Build in tissue** — hand the growth program to a stem cell lab *(awaiting wet lab partner)*

Steps 1-6 demonstrated computationally on fly and mouse.

## Key results

| Finding | Detail |
|---------|--------|
| 26 architectures ranked | Cellular automaton #1 (509 total). Full rankings across 5 tasks. |
| Composites work | No degradation up to 10 regions / 28K neurons. Linear time scaling. |
| Self-monitoring | Tier 1 self-prediction 85%. Tier 2: 24% mean. Tier 3 recursive: 12% mean. |
| Growth from spec | Nav score 851 vs real brain 577. No connectome data used. |
| Cross-species | Hub-and-spoke conserved across fly and mouse (600M years divergence). |
| Minimum viable | 3,000 neurons. Below that, circuits are dead. |
| Adaptation | Reservoir: real habituation + 3.4x novelty detection. Reward-modulated: 5x. |
| Architecture determines function | Growth stimulation protocol doesn't matter. |
| 9/10 predictions confirmed | Including untargeted +58% escape improvement from navigation optimization. |
| Honest negatives | Distraction resistance retracted. Attention compiled weakly. Edge scale sensitivity reported. |

## Architecture catalog

27 architectures across 7 categories, each expressible as a developmental recipe:

**Routing** — Hub-and-spoke, Hierarchical hub, Flat/Distributed, Bus, Ring
**Computation** — Reservoir, Feedforward pipeline, Recurrent attractor, Oscillatory, Predictive coding, Sparse distributed memory
**Control** — Observer-controller, Winner-take-all, Evidence accumulator, Priority queue, Subsumption
**Learning** — Hebbian assembly, Reward-modulated, Neuromodulatory gain control
**Robustness** — Triple redundancy, Graceful degradation, Self-repairing
**Exotic** — Content-addressable memory, Dataflow, Cellular automaton, Hyperdimensional computing, Spiking state machine

See [`latent/ml/compile/architecture_catalog.md`](latent/ml/compile/architecture_catalog.md) for the full catalog with scores and growth program specs.

## Repository structure

```
latent/
├── ml/
│   ├── compile/              # Python library
│   │   ├── architecture_specs.py  # 27 architecture developmental specs
│   │   ├── evolve.py         # (1+1) ES evolution loop
│   │   ├── simulate.py       # Izhikevich neuron model
│   │   ├── fitness.py        # Behavioral fitness functions
│   │   └── data.py           # Connectome data loading
│   ├── experiments/          # All experiment scripts
│   ├── worker/               # FastAPI ML worker service
│   └── results/              # Experiment outputs
├── frontend/                 # Next.js platform (compile.now)
├── backend/                  # Go API server
└── infrastructure/           # Docker, deployment
```

## Environment variables

```bash
# Required for ML worker
COMPILE_DATA_DIR=/path/to/flywire/data

# Required for AI features (behavior classification, architecture recommendation)
OPENAI_API_KEY=
OPENAI_ORG_ID=

# Required for auth
JWT_SECRET=
JWT_REFRESH_SECRET=
WEBAUTHN_RP_ID=
WEBAUTHN_RP_ORIGIN=
WEBAUTHN_RP_NAME=

# Database
DATABASE_URL=postgres://compile:password@localhost:5432/compile
```

See [`latent/backend/.env.example`](latent/backend/.env.example) for the full list.

## Built on

- **[FlyWire Consortium](https://flywire.ai)** — Complete adult fly brain connectome (139,255 neurons)
- **[Eon Systems](https://eon.systems)** — Embodied fly brain simulation (91% behavioral accuracy)
- **[MICrONS / Allen Institute](https://www.microns-explorer.org)** — Mouse V1 cortex connectome

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Open source following FlyWire and Eon. PRs welcome.

## License

CC BY-NC 4.0 — see [LICENSE](LICENSE). Free for research. Commercial use requires permission.

## Contact

Mohamed El Tahawy — [founders@compile.now](mailto:founders@compile.now) — [compile.now](https://compile.now)
