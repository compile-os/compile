# Biological Neural Circuit Architecture Catalog
## Every architecture expressible as a developmental recipe

---

## CATEGORY 1: ROUTING ARCHITECTURES
How information flows from input to output.

### 1.1 Hub-and-Spoke (Biological Default)
**Source:** Observed in fly (modules 4, 19), mouse (L5, L2/3), and all known connectomes.
**Structure:** 2-3 high-connectivity hub nodes route all inter-module communication. Sensory modules connect to hubs. Hubs connect to motor output.
**Growth program:** 15-19 cell types. 2-3 hub types with 5-10x connectivity density. Remaining types are peripheral.
**Tradeoffs:** Precise behavioral control. Limited capacity (~10 behaviors before hub saturation). Single point of failure. Minimal wiring cost.
**Best for:** Organisms that need decisive, fast action selection. Reactive behavior. Motor control.

### 1.2 Hierarchical Hub (Mammalian Strategy)
**Source:** Thalamo-cortical loops, prefrontal gating of basal ganglia, cortical layer hierarchy.
**Structure:** Multiple tiers of hubs. Tier 1 hubs gate motor output. Tier 2 hubs gate which Tier 1 hubs are active. Tier 3 hubs gate Tier 2.
**Growth program:** 25-40 cell types across 3 tiers. Each tier has its own hub types. Inter-tier connections are sparse and specific. Growth order: Tier 1 first (motor control), then Tier 2 (selection), then Tier 3 (meta-control).
**Tradeoffs:** Dramatically more behavioral capacity. Slower decision-making (signals traverse multiple tiers). More cell types = more complex growth program. Enables cognitive control and potentially metacognition.
**Best for:** Complex behavior requiring context-dependent action selection. Working memory. Planning. Anything requiring "thinking before acting."

### 1.3 Flat/Distributed Routing
**Source:** Theoretical. Small-world networks. Some invertebrate ganglia.
**Structure:** No node exceeds 2x average connectivity. Information flows through many parallel low-bandwidth paths instead of few high-bandwidth hubs.
**Growth program:** All cell types have similar connectivity density. Connection rules emphasize local clustering with sparse long-range shortcuts (small-world topology). Fewer cell types needed (maybe 8-12) but more connection rules.
**Tradeoffs:** Robust to damage (no single point of failure). Poor behavioral control (no gating bottleneck — activity leaks to motors). Slow convergence to decisions. May require external gating mechanism.
**Best for:** Distributed sensing. Swarm-like behavior. Systems where robustness matters more than precision.

### 1.4 Bus Architecture
**Source:** Computer bus (shared communication channel). Some features of the insect ventral nerve cord.
**Structure:** A single shared "bus" module that all other modules read from and write to. Not a hub (doesn't process) — just a communication channel. Every module broadcasts its state to the bus. Every module reads the bus to decide what to do.
**Growth program:** One elongated cell type forming the bus (could be a tract of parallel axons). All other cell types connect to the bus with read/write connections. Spatial layout: bus runs through the center, modules arrayed along it.
**Tradeoffs:** Simple wiring. All modules have equal access. Bandwidth-limited (one bus, many speakers). No inherent gating — needs an arbitration mechanism.
**Best for:** Simple multi-module coordination. Situations where all modules need shared state awareness.

### 1.5 Ring Architecture
**Source:** Token ring networks. Some annelid (worm) nervous systems where ganglia are arranged in a chain/ring.
**Structure:** Modules arranged in a ring. Each module connects only to its neighbors. Information circulates around the ring. A "token" of activation determines which module currently controls motor output.
**Growth program:** N cell types arranged spatially in a ring. Each type connects to its two neighbors. One "token" cell type that circulates activation. Growth order follows the ring sequence.
**Tradeoffs:** Fair access (every module gets a turn). Predictable timing. Latency proportional to ring size. Simple growth program. No single point of failure.
**Best for:** Sequential processing. Rhythmic behaviors. Central pattern generators. Anything that naturally cycles through states.

---

## CATEGORY 2: COMPUTATION ARCHITECTURES
How the circuit computes.

### 2.1 Reservoir Computing
**Source:** Echo state networks, liquid state machines. Loosely inspired by cortical microcircuits.
**Structure:** Large, randomly connected recurrent core ("reservoir") that produces rich dynamics. Small, trained readout layer extracts specific computations from the reservoir dynamics.
**Growth program:** One large population of recurrently connected excitatory/inhibitory neurons (standard E/I ratio ~80/20). Connection density ~5-15%. One small readout population connected to the reservoir with plastic synapses refined by activity-dependent growth. The reservoir itself does NOT need specific wiring.
**Tradeoffs:** Extremely simple growth program for the core (random is fine — organoids already produce this). All computational specificity is in the readout. Flexible — same reservoir supports many readouts for different tasks. Hard to get precise temporal control. Reservoir dynamics can be chaotic.
**Best for:** Pattern recognition. Temporal sequence processing. Any task where the input is complex and the output is a classification or simple decision. Closest to what current organoids already do.

### 2.2 Feedforward Pipeline
**Source:** Retinal processing, early visual cortex (V1→V2→V4→IT), deep neural networks.
**Structure:** Layers of processing stages. Information flows in one direction. Each layer transforms the representation. No recurrence within the pipeline.
**Growth program:** N cell types arranged in spatial layers. Each layer connects to the next. No within-layer or backward connections. Growth order: layer 1 first, then 2, etc. Activity-dependent refinement happens within each layer.
**Tradeoffs:** Fast (single pass through the pipeline). No memory (no recurrence). Predictable latency. Easy to analyze. Cannot do temporal integration or working memory.
**Best for:** Rapid sensory processing. Feature extraction. Reflexes. Any computation that maps input to output without needing to remember anything.

### 2.3 Recurrent Attractor Network
**Source:** Hopfield networks. Hippocampal place cells. Prefrontal persistent activity.
**Structure:** Strongly recurrently connected population that settles into stable activity patterns (attractors). Each attractor represents a stored state or memory. Input pushes the network toward one attractor or another.
**Growth program:** One primary cell type with strong recurrent excitatory connections. One inhibitory cell type providing global inhibition (winner-take-all dynamics). Connection strengths encode the attractors — this requires activity-dependent plasticity during growth to "burn in" the attractor states.
**Tradeoffs:** Natural memory (attractors persist without input). Pattern completion (partial input → full attractor). Limited capacity (number of attractors scales with neuron count). Slow switching between states. Can get stuck.
**Best for:** Working memory. Decision-making (each option is an attractor). Pattern recognition with noise tolerance. State maintenance.

### 2.4 Oscillatory Computation
**Source:** Gamma oscillations in cortex. Theta rhythms in hippocampus. Central pattern generators in spinal cord.
**Structure:** Populations of neurons that oscillate at defined frequencies. Computation happens through phase relationships between oscillators. Two signals are "bound" when their oscillators synchronize.
**Growth program:** Pairs of E/I cell types tuned to specific frequencies (frequency determined by time constants, which are determined by ion channel expression — specifiable in a growth program). Inter-oscillator connections allow phase locking. Different frequencies for different computational roles (e.g., 40Hz for local binding, 8Hz for memory encoding).
**Tradeoffs:** Natural temporal coordination. Multiplexing (different frequencies carry different information simultaneously). Requires precise timing — sensitive to parameter tuning. Complex growth program (ion channel specification).
**Best for:** Temporal binding. Attention (oscillatory gating). Rhythm generation. Motor pattern generation. Multi-sensory integration via phase synchronization.

### 2.5 Predictive Coding
**Source:** Karl Friston's free energy principle. Rao & Ballard's predictive coding in visual cortex.
**Structure:** Paired layers at each level: a prediction layer generates expected input, a comparison layer computes prediction error. Prediction errors flow up the hierarchy. Predictions flow down. The circuit minimizes surprise by updating its internal model.
**Growth program:** Two cell types per level (predictor and error). Connections: predictor→error (same level, inhibitory — subtracts prediction from reality), error→predictor (next level up, excitatory — drives model updates), predictor→predictor (top-down, excitatory — sends predictions down). 3 levels = 6 cell types + connection rules.
**Tradeoffs:** Adaptive — learns to predict its environment. Efficient — only transmits surprise (prediction errors), not redundant expected signals. Complex growth program. Requires structured top-down and bottom-up connectivity. Slow to learn initially.
**Best for:** Sensory processing in changing environments. Adaptation. Learning. Any system that needs to build an internal model of its world.

### 2.6 Sparse Distributed Memory
**Source:** Pentti Kanerva's SDM. Cerebellar granule cell layer.
**Structure:** Enormous number of simple units (granule cells) sparsely activated by any given input. Each input activates a random ~1% of units. Storage by modifying the outputs of activated units. Retrieval by activating the same ~1% and reading out.
**Growth program:** One very numerous cell type (granule equivalent — 80% of neurons). One input cell type with divergent connectivity (each input connects to many granule cells randomly). One readout cell type with convergent connectivity. The sparsity emerges from the divergent→convergent architecture.
**Tradeoffs:** Massive capacity (scales exponentially with neuron count). Naturally content-addressable. Robust to noise. Requires many neurons for the sparse layer. Simple individual computations.
**Best for:** Associative memory. Pattern storage and retrieval. Motor learning (this is literally what the cerebellum does). Situations where you need to store many patterns and retrieve them by partial match.

---

## CATEGORY 3: CONTROL ARCHITECTURES
How the circuit decides what to do.

### 3.1 Observer-Controller Separation
**Source:** Modern control theory. Kalman filters. Not cleanly implemented in any known brain region but elements exist in cerebellum (forward model) + basal ganglia (controller).
**Structure:** Two distinct modules. Observer: integrates sensory input and estimates the current state of the world. Controller: takes the estimated state and selects an action. Connected by a narrow interface (estimated state vector).
**Growth program:** Two spatial regions with distinct cell types. Observer region: recurrent, integrative, many sensory inputs. Controller region: feedforward, few inputs (from observer), direct motor output. Interface layer: small number of projection neurons connecting the two.
**Tradeoffs:** Clean modularity. Observer can be complex without affecting controller speed. Controller can be simple and fast. Easy to swap controllers for different tasks while keeping the same observer. Requires the interface to be well-specified.
**Best for:** Systems operating in complex sensory environments where state estimation is hard but action selection should be fast. Robotics-style applications.

### 3.2 Winner-Take-All
**Source:** Lateral inhibition in retina. Decision-making circuits in LIP. Competitive neural networks.
**Structure:** N modules representing N options. Each module excites itself and inhibits all others. The module with the strongest input wins and suppresses the rest. Only one module active at a time.
**Growth program:** N copies of the same cell type (one per option). One inhibitory cell type that receives input from all modules and inhibits all modules (global inhibition). Self-excitation within each module via recurrent connections. Growth order doesn't matter — architecture is symmetric.
**Tradeoffs:** Fast, clean decisions. Only one thing happens at a time. Cannot represent uncertainty or mixed states. Hard to reverse a decision once the winner suppresses alternatives.
**Best for:** Action selection. Categorical decisions. Any situation where exactly one option must be chosen.

### 3.3 Evidence Accumulator (Drift-Diffusion)
**Source:** Gold & Shadlen's decision-making model. Lateral intraparietal cortex. Superior colliculus.
**Structure:** Two competing populations that each accumulate evidence for their preferred option over time. When one population reaches a threshold, that option is selected. A threshold-detecting output neuron triggers the action.
**Growth program:** Two matched populations of excitatory neurons with self-excitation and mutual inhibition (like winner-take-all but with slower dynamics). One threshold cell type that fires only when input exceeds a specific level. The threshold is set by the inhibitory interneuron properties (tunable in the growth program through ion channel specification).
**Tradeoffs:** Naturally handles noisy evidence. Speed-accuracy tradeoff is built in (lower threshold = faster but less accurate). Represents confidence (how far above threshold). Slower than winner-take-all.
**Best for:** Perceptual decisions under uncertainty. Any choice that benefits from integrating evidence over time rather than snapping to a decision.

### 3.4 Priority Queue (Urgency Gating)
**Source:** Cisek & Kalaska's affordance competition model. Basal ganglia direct/indirect pathway.
**Structure:** Multiple action options maintained in parallel, each tagged with a priority score. A gating mechanism selects the highest-priority action. Priority is modulated by urgency (time pressure), value (expected reward), and context. Actions can be queued and re-prioritized dynamically.
**Growth program:** One module per potential action (similar to WTA). One priority-tagging cell type that modulates each module's activation based on contextual inputs. One neuromodulatory cell type (dopaminergic) that broadcasts urgency/value signals globally. Gating output layer that reads the highest-activation module.
**Tradeoffs:** Flexible — can switch priorities dynamically. Handles multiple pending actions. More complex growth program (needs neuromodulatory cell type). Risk of priority inversion (low-priority action blocking high-priority one).
**Best for:** Complex behavioral scheduling. Foraging (find food vs. avoid predator vs. find mate, dynamically prioritized). Any organism managing multiple concurrent goals.

### 3.5 Subsumption Architecture
**Source:** Rodney Brooks' behavior-based robotics. Layered insect behavior models.
**Structure:** Behaviors stacked in layers. Lower layers handle basic reflexes (escape, avoidance). Higher layers handle complex behaviors (navigation, foraging). Higher layers can SUPPRESS lower layers when active, but lower layers can always override higher layers for safety (escape overrides navigation). No central controller.
**Growth program:** Distinct cell type populations for each behavioral layer. Lower layers have direct sensory-motor connections. Higher layers connect through intermediate interneurons. Suppression connections: each layer has inhibitory output to the layer below it. Override connections: emergency sensory input (threat detection) bypasses all layers and directly activates escape motor output.
**Tradeoffs:** No central bottleneck. Reactive and fast for low-level behaviors. Higher behaviors emerge from layered suppression without planning. Limited capacity for complex cognition. Excellent for embodied agents.
**Best for:** Insect-scale behavior. Simple robots. Any system where fast reflexes matter and cognitive overhead should be minimal. Your fly circuit is already close to this.

---

## CATEGORY 4: LEARNING AND ADAPTATION ARCHITECTURES
How the circuit changes over time.

### 4.1 Hebbian Assembly
**Source:** Hebb's cell assembly theory. Hippocampal sharp-wave ripples. Cortical engrams.
**Structure:** Neurons that fire together wire together. Initial connectivity is broad and weak. Activity-dependent plasticity strengthens co-activated connections and weakens others. Stable assemblies (engrams) emerge representing learned patterns.
**Growth program:** One excitatory cell type with broad initial connectivity. One inhibitory cell type providing homeostatic regulation (prevents runaway excitation). Plasticity rules specified as part of the growth program: STDP time window, learning rate, homeostatic target firing rate. The initial circuit is generic — specificity emerges through experience.
**Tradeoffs:** Self-organizing. No external training signal needed. Learns from environment directly. Can be unstable (runaway potentiation or catastrophic forgetting). Capacity limited by homeostatic constraints.
**Best for:** Associative learning. Memory formation. Sensory map formation. Any system that needs to adapt to its specific environment after being grown.

### 4.2 Reward-Modulated Architecture
**Source:** Dopaminergic reward prediction error. Basal ganglia reinforcement learning. TD learning.
**Structure:** A standard processing circuit (any architecture above) plus a reward module. The reward module receives outcome signals and broadcasts a global neuromodulatory signal (dopamine equivalent). The global signal gates plasticity: connections that were active when reward arrives are strengthened. Connections active when punishment arrives are weakened.
**Growth program:** Base circuit (any architecture) + one dopaminergic cell type + one reward-input cell type. Dopaminergic neurons project broadly to the base circuit. Plasticity rules: three-factor learning (pre-synaptic activity × post-synaptic activity × dopamine signal). Growth order: base circuit first, dopaminergic overlay second.
**Tradeoffs:** Learns from outcomes rather than just correlations. Can learn arbitrary input-output mappings given reward signal. Requires a reward signal (who decides what's rewarding?). Slower learning than Hebbian. More biologically realistic.
**Best for:** Behavioral shaping. Goal-directed learning. Any system that needs to learn what to DO (not just what patterns exist) based on outcomes.

### 4.3 Neuromodulatory Gain Control
**Source:** Serotonin, norepinephrine, acetylcholine systems in mammals. Octopamine/tyramine in insects.
**Structure:** Base circuit (any architecture) + multiple neuromodulatory populations, each broadcasting a different signal that changes the GAIN of processing in the base circuit. One modulator increases overall excitability (arousal). Another increases signal-to-noise ratio (attention). Another shifts the speed-accuracy tradeoff (urgency).
**Growth program:** Base circuit + 2-4 neuromodulatory cell types, each with distinct neurotransmitter identity and broad projection patterns. Each modulator type has specific receptor expression in the base circuit, determining which modules it affects. Growth order: base circuit first, modulatory overlay second.
**Tradeoffs:** Dramatic behavioral flexibility from a small number of additional cell types. The same circuit can operate in multiple "modes" depending on neuromodulatory state. Complex to tune — interactions between modulators can be unpredictable.
**Best for:** Behavioral state switching (alert vs. resting, focused vs. exploratory). Emotional regulation. Stress response. Sleep/wake transitions.

---

## CATEGORY 5: ROBUSTNESS ARCHITECTURES
How the circuit handles damage and noise.

### 5.1 Triple Modular Redundancy
**Source:** Fault-tolerant computing. Space shuttle avionics. Not directly observed in biology (bilateral symmetry gives 2x redundancy).
**Structure:** Three copies of the critical circuit. A voting layer compares outputs. Majority wins. Any single copy can fail completely and the system continues operating correctly.
**Growth program:** Three spatial copies of the hub cell types at defined positions. One voting cell type that receives input from all three copies and outputs the majority signal. 3x the hub neurons but same peripheral circuit.
**Tradeoffs:** Survives single-point failures. 3x cost for hub components. Voting layer adds latency. Truly robust to damage.
**Best for:** Safety-critical applications. Brain repair (design circuits that tolerate partial damage). Any application where reliability matters more than efficiency.

### 5.2 Graceful Degradation (Population Coding)
**Source:** Motor cortex population vectors. Place cell populations in hippocampus.
**Structure:** Information encoded across a population, not in single neurons. Each neuron contributes a small amount to the representation. Losing 10% of neurons degrades performance by ~10%, not catastrophically.
**Growth program:** One large population of similar neurons with overlapping tuning. No individual neuron is critical. Connection rules ensure distributed, overlapping representations. Readout averages across the population.
**Tradeoffs:** Naturally robust to neuron loss. Degrades proportionally, not catastrophically. Requires more neurons than a sparse code. Less precise than single-neuron coding.
**Best for:** Motor control (graceful degradation when neurons die). Aging-resilient circuits. Any application where gradual decline is acceptable but sudden failure is not.

### 5.3 Self-Repairing Architecture
**Source:** Axonal sprouting after injury. Cortical remapping after stroke. Neurogenesis in hippocampus.
**Structure:** Base circuit (any architecture) + a population of uncommitted progenitor cells that can differentiate and integrate on demand. When circuit damage is detected (loss of activity in a region), progenitor cells receive proliferation signals, differentiate into the needed cell type, and wire in following activity-dependent rules.
**Growth program:** Base circuit + one progenitor cell type maintained in an undifferentiated state. Differentiation rules: if local activity drops below threshold, progenitor differentiates into the most common local cell type and follows standard connection rules. This is speculative but biologically plausible — adult neurogenesis exists in hippocampus and olfactory bulb.
**Tradeoffs:** Self-healing. Requires maintaining progenitor cells (metabolic cost). Repair is slow (days to weeks for new neurons to integrate). Repaired circuit may not be identical to original.
**Best for:** Long-duration applications. Implanted circuits that need to last years. Brain repair tissue designed to maintain itself.

---

## CATEGORY 6: EXOTIC ARCHITECTURES
Novel designs not observed in biology, theoretically growable.

### 6.1 Content-Addressable Memory (Biological Hash Table)
**Source:** Bloom filters. Hash tables. Loosely related to cerebellar lookup.
**Structure:** Input is "hashed" through a fixed random projection to a sparse code. The sparse code addresses a memory location. Storage and retrieval are O(1) — direct lookup, no search. Collisions handled by the sparse code's low overlap.
**Growth program:** Input layer → random divergent projection (granule cell equivalent) → sparse intermediate layer → convergent readout. The random projection is the "hash function." It doesn't need to be learned — random connectivity works. Readout connections are plastic.
**Tradeoffs:** Extremely fast retrieval. Fixed capacity determined by sparse layer size. No graceful degradation at capacity — hard failure when full. Cannot generalize (exact match only).
**Best for:** Lookup tables. Motor programs stored by context. Fast stimulus-response mapping. Immune-system-like pattern matching.

### 6.2 Dataflow Architecture
**Source:** Dataflow computing. Kahn process networks. Some features of retinal processing.
**Structure:** No central clock or controller. Each module activates when all its inputs are ready (data-driven execution). Modules fire asynchronously. The computation "flows" through the network driven by data availability rather than a central scheduler.
**Growth program:** Modules defined by cell type. Each module has threshold logic: fires only when N of M inputs are active. No global timing mechanism. Connection rules define the dataflow graph. Growth order matches the expected data flow (sensory modules first, motor modules last).
**Tradeoffs:** Naturally parallel. No timing bottleneck. Self-scheduling. Difficult to debug (no global state). Hard to implement sequential logic. Computation speed depends on input rate.
**Best for:** Sensory processing pipelines. Parallel feature extraction. Any computation that is naturally expressed as a graph of independent operations.

### 6.3 Neuronal Cellular Automaton
**Source:** Cellular automata (Conway's Game of Life, Wolfram). Grid-based neural architectures.
**Structure:** Neurons arranged in a regular 2D or 3D grid. Each neuron connects only to its immediate spatial neighbors. Simple local rules determine each neuron's state based on neighbor states. Complex global behavior emerges from local interactions.
**Growth program:** One cell type arranged in a regular grid. Connection rules: connect to all cells within radius R. Update rules: fire if K of N neighbors are active. Extremely simple growth program — just spatial arrangement and a radius.
**Tradeoffs:** Theoretically universal computation (some cellular automata are Turing complete). Extremely simple growth program. Behavior is hard to predict from rules. Slow (information propagates one cell per timestep). Large grid needed for complex computation.
**Best for:** Morphogenesis modeling. Texture generation. Pattern formation. Proof-of-concept that simple developmental rules can produce complex computation.

### 6.4 Hyperdimensional Computing
**Source:** Pentti Kanerva's computing with high-dimensional vectors. Tony Plate's holographic reduced representations.
**Structure:** Information represented as high-dimensional random vectors (~10,000 dimensions). Operations: binding (component-wise multiply), bundling (component-wise add), permutation (shift). Extremely noise-tolerant because random high-dimensional vectors are nearly orthogonal.
**Growth program:** Large population of neurons where each neuron represents one dimension. Binding implemented by paired inhibitory connections. Bundling implemented by convergent excitatory connections. Each "symbol" is a random activation pattern across the population. Retrieval by similarity matching.
**Tradeoffs:** Naturally robust to noise and damage. Elegant algebraic operations on distributed representations. Requires large populations. Operations are approximate, not exact.
**Best for:** Symbolic reasoning in a neural substrate. Language-like compositional representations. Analogy and relational reasoning. Any task that requires combining discrete symbols while maintaining neural plausibility.

### 6.5 Spiking Neural State Machine
**Source:** Finite state machines implemented in spiking networks. Theoretical computational neuroscience.
**Structure:** Distinct neural populations representing each state. Exactly one population active at a time (maintained by winner-take-all dynamics). Transitions triggered by specific input patterns. Each state has associated output connections to motor layer.
**Growth program:** N cell types (one per state). Winner-take-all inhibition between states. Transition connections: specific sensory input + current state → next state activation. Motor output connections from each state. Growth order: state populations first, transition connections second.
**Tradeoffs:** Predictable, verifiable behavior (finite state machines are well-understood). Limited to finite states. Cannot represent continuous values. Simple to analyze and debug.
**Best for:** Protocol execution. Behavioral sequences. Safety-critical state transitions (only allowed transitions are wired). Any task naturally described as a state diagram.

---

## CATEGORY 7: COMPOSITE ARCHITECTURES
Combinations that leverage multiple principles.

### 7.1 Reservoir + Hub Readout
Reservoir core for rich dynamics. Hub-and-spoke readout for precise behavioral control. Combines the flexibility of reservoir computing with the gating control of hub architecture.

### 7.2 Hierarchical Hub + Predictive Coding
Each tier of the hub hierarchy implements predictive coding. Lower tiers predict sensory input. Higher tiers predict lower-tier prediction errors. The hierarchy naturally implements a deep generative model with behavioral control at each level.

### 7.3 Subsumption + Reward Modulation
Layered reactive behaviors (subsumption) with a dopaminergic reward system that adjusts which layer dominates in which context. Basic reflexes are hardwired. Higher behaviors are reward-shaped.

### 7.4 Observer-Controller + Evidence Accumulator
Observer estimates world state. Controller uses drift-diffusion to select actions under uncertainty. Clean separation of "what's happening" from "what should I do about it."

### 7.5 Oscillatory + Winner-Take-All
Multiple WTA circuits operating at different frequencies. Gamma-frequency WTA for fast local decisions. Theta-frequency WTA for slow global decisions. Phase coupling between frequencies for cross-scale coordination.

---

## EXPERIMENTAL RESULTS (2026-03-23)

All 26 architectures tested across 5 tasks with biologically realistic simulation: Izhikevich neurons, short-term synaptic depression (U=0.2, tau=800ms), neuron type diversity, 3,000 neurons per circuit, 3 seeds × 50 generations.

| # | Architecture | Nav | Esc | Turn | Conflict | WM | Total | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | **Cellular Automaton** | 100 | 99 | 12 | 10 | **288** | **509** | Validated |
| 2 | **Spiking State Machine** | 69 | 68 | 8 | 9 | **197** | **351** | Validated |
| 3 | **Winner-Take-All** | 65 | 60 | 8 | **12** | 139 | **285** | Validated |
| 4 | Population Coding | 40 | 42 | 6 | 8 | 115 | 211 | Validated |
| 5 | Evidence Accumulator | 37 | 33 | 6 | 8 | 82 | 166 | Validated |
| 6 | Reservoir | 22 | 25 | 7 | 8 | 54 | 115 | Validated |
| 7 | Subsumption | 23 | 26 | 5 | **11** | 48 | 113 | Validated |
| 8 | Hierarchical Hub | 22 | 20 | 4 | 6 | 50 | 102 | Validated |
| 9 | Recurrent Attractor | 21 | 23 | 5 | 7 | 44 | 99 | Validated |
| 10 | Priority Queue | 16 | 14 | 6 | 10 | 35 | 80 | Validated |
| 11 | Reward Modulated | 15 | 13 | 5 | 7 | 35 | 75 | Validated |
| 12 | Neuromodulatory Gain | 14 | 14 | 4 | 6 | 32 | 70 | Validated |
| 13 | Self-Repairing | 13 | 13 | 4 | 8 | 26 | 64 | Validated |
| 14 | Observer-Controller | 11 | 11 | 3 | 6 | 28 | 60 | Validated |
| 15 | Flat Distributed | 23 | 22 | 4 | 5 | **0** | 54 | Validated |
| 16 | Bus | 17 | 15 | 5 | 5 | **0** | 42 | Validated |
| 17 | Hebbian Assembly | 9 | 8 | 3 | 6 | 15 | 42 | Validated |
| 18 | Ring (CPG) | 3 | 5 | 2 | 5 | 8 | 23 | Validated |
| 19 | Feedforward Pipeline | 2 | 4 | 1 | 2 | 0 | 9 | Validated |
| 20 | Hyperdimensional | 1 | 2 | 0 | 3 | 2 | 8 | Validated |
| 21 | Triple Redundancy | 1 | 1 | 1 | 2 | 0 | 4 | Validated |
| 22 | Predictive Coding | 1 | 1 | 0 | 1 | 0 | 3 | Validated |
| 23 | Dataflow | 0 | 1 | 0 | 1 | 0 | 2 | Validated |
| 24 | Content-Addressable | 0 | 1 | 0 | 1 | 0 | 2 | Validated |
| 25 | Oscillatory | 0 | 0 | 0 | 0 | 0 | 1 | Needs Izhikevich |
| 26 | Sparse Distributed Mem | 0 | 0 | 0 | 0 | 0 | 0 | Needs >100K neurons |

Reference: Hub-and-Spoke (biological FlyWire) = 851 nav score with full growth program.

### Key Findings

- **Architecture selection matters.** Flat distributed scores 0 on working memory. Cellular automaton scores 288. Different architectures for different tasks.
- **Simplest wins reactive + memory.** Cellular automaton (grid, local connections, 2 cell types) dominates. Complexity doesn't help for basic behaviors.
- **Composites work.** CA + WTA composite matches or exceeds either alone on all tasks. No degradation from simultaneous multi-behavior operation (CA scores 84.68 on combined nav+conflict+WM).
- **Minimum viable size: ~3,000 neurons.** Below that, circuits are dead.
- **Reservoir shows real adaptation.** Habituation + 3.4x novelty response. Reward-modulated: 6x novelty. Fifth computational dimension validated.
- **Self-prediction is a compilable behavior.** Reservoir predicts own output at 85% correlation. Sixth computational dimension.
- **Recursive self-monitoring works.** 3-tier composite (navigate + predict navigator + predict predictor). Tier 3 at 12.3% mean across 10 seeds (7/10 > 5%, peak 40%). Consistent signal, not noise.
- **Rhythm is weak but present.** Proper alternation metric: CA 5.44, ring/CPG 0.41, oscillatory 0 (needs Izhikevich).
- **Growth stimulation doesn't matter.** Structured vs random: identical results for CA and WTA.
- **Composites scale to 10 regions (28K neurons) with no degradation.** Nav score 97-99 at all scales. Grow 11s, evolve 105s. Architecture complexity has no ceiling at this scale.
- **Simultaneous multi-behavior works.** CA scores 84.68 on combined nav+conflict+WM. Circuits don't need separate modes for separate behaviors.

### Computational Dimensions (7 validated)

| Dimension | Best Architecture | Score | Validated? |
|---|---|---|---|
| Speed | Cellular Automaton | 100 (nav) | Yes |
| Persistence | Cellular Automaton | 288 (WM) | Yes |
| Competition | Winner-Take-All | 11.7 (conflict) | Yes |
| Adaptation | Reward Modulated | 6x novelty | Yes |
| Self-Prediction | Reservoir | 85% correlation | Yes |
| Rhythm | Cellular Automaton | 5.44 (alternation) | Weak |
| Gating | Hierarchical Hub | theoretical | Not tested |

## GROWTH PROGRAM COMPLEXITY

| Architecture | Cell Types | Connection Rules | Growth Order Critical? |
|---|---|---|---|
| Hub-and-Spoke | 15-19 | 30 | Yes |
| Hierarchical Hub | 16 | 10 | Yes |
| Flat/Distributed | 10 | 5 | No |
| Bus | 7 | 6 | No |
| Ring (CPG) | 10 | 26 | Yes |
| Reservoir | 5 | 6 | No |
| Feedforward Pipeline | 8 | 9 | Yes |
| Recurrent Attractor | 4 | 5 | No |
| Oscillatory | 7 | 9 | No |
| Predictive Coding | 8 | 9 | Yes |
| Sparse Distributed | 6 | 7 | No |
| Observer-Controller | 7 | 9 | Yes |
| Winner-Take-All | 7 | 5 | No |
| Evidence Accumulator | 6 | 11 | No |
| Priority Queue | 8 | 8 | No |
| Subsumption | 8 | 24 | Yes |
| Triple Redundancy | 7 | 8 | No |
| Population Coding | 5 | 6 | No |
| Self-Repairing | 6 | 7 | No |
| Content-Addressable | 7 | 6 | No |
| Dataflow | 8 | 9 | No |
| Cellular Automaton | 4 | 4 | No |
| Hyperdimensional | 6 | 7 | No |
| State Machine | 8 | 6 | No |

### Calibration Method (2026-03-22)

Architecture specs with made-up connection probabilities produce dead circuits. The fix: calibrate every spec against real FlyWire v783 connectome data.

**Biological operating ranges** extracted from FlyWire functional group analysis:
- Sensory → processing: 0.002–0.02 (very sparse, multi-hop routing)
- Processing → motor: 0.08–0.24 (dense, direct output)
- Inhibition/gating: 0.04–0.10
- Recurrent/lateral: 0.015–0.035
- Cross-module: 0.005–0.015
- Weight distribution: median=2, mean=3.6, p95=12, p99=32 (heavily right-skewed)

Subsumption was directly calibrated from FlyWire (connection probabilities extracted from real DN upstream functional groups). Other architectures use the same biological operating ranges mapped to their connection types. See `architecture_specs.py` for calibrated specs.

---

## WHAT MAKES AN ARCHITECTURE GROWABLE?

An architecture is expressible as a developmental recipe if and only if you can specify:
1. The cell types (how many, what neurotransmitter, what ion channels)
2. The proportions (how many of each type)
3. The spatial layout (where each type goes in 3D)
4. The connection rules (which types connect to which, with what probability at what distance)
5. The growth order (which types differentiate and wire first)
6. The activity-dependent refinement rules (how connections change based on neural activity)

Every architecture in this catalog meets these criteria. The question is not "can we design it" but "can we compile behaviors onto it and grow functional circuits from it."

That is what Compile does.
