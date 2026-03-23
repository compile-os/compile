# Connectome Autoresearch

Autonomous research on the FlyWire connectome — the complete wiring diagram of the adult fruit fly brain (139,255 neurons, 3.7 million connections).

## Goal

Discover novel structural or functional principles in brain wiring. Each experiment proposes a hypothesis, tests it against the real connectome, compares to a null model, and reports whether the finding is significant and surprising.

## Setup

1. **Agree on a run tag**: e.g. `mar13-connectome`. Branch `autoresearch/<tag>` must not exist.
2. **Create branch**: `git checkout -b autoresearch/<tag>`
3. **Read files**:
   - `prepare_connectome.py` — READ ONLY. Data loading, graph building, null models, utilities.
   - `analysis.py` — THE FILE YOU MODIFY. Hypothesis, analysis code, statistical test.
4. **Verify data**: Check that `~/neurodata/flywire/FAFB_v783/` contains `consolidated_cell_types.csv.gz` and `connections_princeton_no_threshold.csv.gz`
5. **Initialize results.tsv**: Create with header row.
6. **Confirm and go**.

## The Data

**Cell types** (`consolidated_cell_types.csv.gz`, ~900KB):
- `root_id`: unique neuron ID
- `cell_type`: predicted type (e.g., 'LC10', 'DNa02')
- `super_class`: broad category ('sensory', 'central', 'motor')
- `nt_type`: neurotransmitter ('GABA', 'glutamate', 'acetylcholine')
- `side`: 'left', 'right', 'center'
- `neuropil`: brain region

**Connections** (`connections_princeton_no_threshold.csv.gz`, ~277MB):
- `pre_root_id`: source neuron
- `post_root_id`: target neuron
- `syn_count`: number of synapses
- `neuropil`: where connection occurs
- `nt_type`: neurotransmitter

It's a directed graph. Nodes are neurons with properties. Edges are synaptic connections with weights.

## What You CAN Do

- Modify `analysis.py` — this is the only file you edit
- Use any functions from `prepare_connectome.py`
- Use standard libraries: numpy, pandas, networkx, scipy, collections
- Propose any hypothesis about brain structure

## What You CANNOT Do

- Modify `prepare_connectome.py`
- Install new packages
- Fabricate results

## Experiment Categories

**Motif Analysis**
- Are certain 3-node patterns enriched vs random graph?
- Do motor circuits have different motifs than sensory circuits?
- Are reciprocal connections more common in certain brain regions?

**Hub Analysis**
- Which neurons sit on many shortest paths (bottlenecks)?
- Are hubs more likely to be inhibitory or excitatory?
- Do hubs connect brain regions or operate within regions?

**Cell Type Prediction**
- Can you predict cell type from connectivity alone?
- Does in/out degree ratio predict sensory vs motor?
- Do neurons of the same type cluster in connectivity space?

**Path Analysis**
- What's the shortest path from sensory input to motor output?
- Are there parallel pathways or single bottlenecks?
- How many hops from any neuron to any other?

**Comparative Analysis**
- Left vs right hemisphere symmetry?
- Are certain cell types lateralized?
- Regional differences in connectivity density?

**Ablation Studies**
- Remove a neuron type — what paths break?
- Which neurons are critical for which pathways?
- Redundancy: can the network route around damage?

## The Experiment Loop

LOOP FOREVER:

1. **Propose hypothesis**: Look at prior results, think about what would be surprising to a neuroscientist. Write a clear, testable hypothesis.

2. **Modify analysis.py**: Update HYPOTHESIS string. Write code to test it. Always compare against a null model (shuffled labels, random graph, etc.).

3. **Git commit**: Commit your changes with a descriptive message.

4. **Run**: `python analysis.py > run.log 2>&1`

5. **Extract results**: `grep "^p_value:\|^is_significant:\|^conclusion:" run.log`

6. **Evaluate**:
   - Is p < 0.05? (significant)
   - Is the effect size meaningful? (not just statistically significant)
   - Has this been published? (check if novel — you can search)
   - Would a neuroscientist find this surprising?

7. **Log to results.tsv**:
   ```
   commit	p_value	is_significant	is_novel	status	hypothesis
   a1b2c3d	0.0012	True	True	keep	Hub neurons enriched for GABA
   ```

8. **Keep or discard**:
   - If significant AND novel: KEEP (advance branch)
   - If not significant OR not novel: DISCARD (git reset)

9. **Repeat**: Based on findings, propose next hypothesis. If you found X, what does that imply about Y?

## Output Format

Your analysis.py should print a summary block:

```
---
hypothesis: <short description>
metric_real: <observed value>
metric_null: <expected under null>
z_score: <standard deviations from null>
p_value: <statistical significance>
is_significant: <True/False>
is_novel: <True/False>
conclusion: <one-line summary>
```

## Null Models

Always compare to a null model. Options in `prepare_connectome.py`:

- `random_graph_preserve_degree(G)`: Random graph with same in/out degree sequence
- `shuffle_node_attributes(G, 'nt_type')`: Shuffle attribute labels
- `random_graph_erdos_renyi(G)`: Random graph with same density

If your finding exists in the null model, it's not meaningful.

## Logging Results

`results.tsv` (tab-separated, NOT committed to git):

```
commit	p_value	is_significant	is_novel	status	hypothesis
```

Status: `keep` (significant + novel), `discard` (not significant), `known` (significant but already published), `crash`

## NEVER STOP

Once experimentation begins, do NOT pause to ask. Run indefinitely until manually stopped. If you run out of ideas:

- Re-read the data columns — what haven't you explored?
- Combine previous findings — if A is true and B is true, what about A+B?
- Go deeper — you found X in brain region Y, does it hold in region Z?
- Invert — you found neurons of type T are enriched for property P, are non-T neurons depleted?

The human may be asleep. You have 8 hours to run 100+ experiments on the most detailed brain wiring diagram that exists. The academic world has published ~30 papers on this data in 1 year. You're running systematic analyses at machine speed.

## What You're Looking For

You don't know in advance. That's the point. You might discover:

- A motif that predicts function
- A hub neuron type that nobody has characterized
- A structural signature that differs left vs right
- A wiring principle that's conserved or violated
- A cell type whose connectivity doesn't match its annotation

Any of these could be publishable. The goal is breadth — run 500 analyses, surface the surprising ones, let the human evaluate which are worth pursuing.
