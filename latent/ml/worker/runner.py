"""
Evolution runner that executes in a subprocess via ProcessPoolExecutor.
Communicates progress back via a multiprocessing.Queue.
"""

from __future__ import annotations

import logging
import multiprocessing
import os
from typing import Any

logger = logging.getLogger(__name__)


def run_evolution_with_progress(
    fitness_name: str,
    seed: int,
    n_generations: int,
    n_mutations: int,
    progress_queue: multiprocessing.Queue,
    architecture: str = "hub_and_spoke",
    use_biological_reference: bool = False,
) -> dict[str, Any]:
    """
    Run evolution and push progress events to the queue.
    This function runs in a separate process.

    Pipeline:
    1. Load architecture spec
    2. Generate connectome from spec (or use biological reference)
    3. Run evolution on generated connectome
    4. Return results tagged with architecture
    """
    try:
        import torch
        from compile.simulate import IzhikevichBrainEngine
        from compile.fitness import FITNESS_FUNCTIONS
        from compile.evolve import run_evolution

        connectome_source = "generated"

        if use_biological_reference:
            # Research path: use the FlyWire biological connectome
            from compile.data import load_connectome, load_module_labels, build_edge_synapse_index

            data_dir = os.environ.get("COMPILE_DATA_DIR", "data")
            if not os.path.isdir(data_dir):
                raise FileNotFoundError(
                    f"Data directory not found: {data_dir}. "
                    "Download FlyWire data and set COMPILE_DATA_DIR."
                )

            logger.info("Loading biological connectome for %s (seed=%d)...", fitness_name, seed)
            df_conn, df_comp, num_neurons = load_connectome()
            labels = load_module_labels()
            edge_syn_idx, inter_module_edges = build_edge_synapse_index(df_conn, labels)

            brain = IzhikevichBrainEngine(num_neurons=num_neurons, device="cpu")
            brain.build_from_connectome(df_conn)
            connectome_source = "biological_reference"
        else:
            # Production path: generate connectome from architecture spec
            from compile.architecture_specs import get_growth_spec

            logger.info("Generating %s connectome for %s (seed=%d)...", architecture, fitness_name, seed)

            spec = get_growth_spec(architecture)
            num_neurons = spec["total_neurons"]

            # Use the sequential activity-dependent growth model to generate connectome
            # For now, build a simple connectome from the spec's connection rules
            # The full growth model integration will use compile.growth when available
            brain = IzhikevichBrainEngine(num_neurons=num_neurons, device="cpu")
            brain.build_from_spec(spec)  # New method that generates from architecture spec

            # Build edge index from generated connectome
            from compile.data import build_edge_synapse_index_from_brain
            labels = brain.get_module_labels()
            edge_syn_idx, inter_module_edges = build_edge_synapse_index_from_brain(brain, labels)

        # Get fitness function
        if fitness_name not in FITNESS_FUNCTIONS:
            raise ValueError(
                f"Unknown fitness function: {fitness_name}. "
                f"Available: {list(FITNESS_FUNCTIONS.keys())}"
            )
        stimulus, fitness_fn = FITNESS_FUNCTIONS[fitness_name]

        # Progress callback that writes to the multiprocessing queue
        def on_progress(gen: int, total: int, current_fitness: float, accepted_count: int):
            progress_pct = int(gen / total * 100)
            progress_queue.put({
                "type": "progress",
                "generation": gen,
                "total": total,
                "progress": progress_pct,
                "current_fitness": current_fitness,
                "accepted_count": accepted_count,
            })

        # Run evolution
        result = run_evolution(
            brain=brain,
            fitness_name=fitness_name,
            fitness_fn=fitness_fn,
            stimulus=stimulus,
            edge_syn_idx=edge_syn_idx,
            inter_module_edges=inter_module_edges,
            seed=seed,
            n_generations=n_generations,
            n_mutations=n_mutations,
            progress_callback=on_progress,
        )

        # Strip the full mutations list from the result (too large for SSE)
        result_summary = {k: v for k, v in result.items() if k != "mutations"}
        result_summary["architecture"] = architecture
        result_summary["connectome_source"] = connectome_source

        # Run persistence test to classify as reactive vs cognitive
        try:
            from worker.regression import run_persistence_test
            persistence = run_persistence_test()
            result_summary["persistence_test"] = persistence
            result_summary["category"] = persistence.get("category", "reactive")
        except Exception as pt_err:
            logger.warning("Persistence test failed: %s", pt_err)
            result_summary["category"] = "reactive"

        progress_queue.put({"type": "done"})
        return result_summary

    except Exception as e:
        logger.exception("Evolution failed")
        progress_queue.put({"type": "error", "message": str(e)})
        raise
