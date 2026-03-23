# Makefile for the compile package (connectome evolution experiments)
#
# Provides targets for installation, testing, linting, formatting,
# and reproducing experiment results. Run `make help` for a summary.

.PHONY: install test lint format reproduce-core reproduce-controls reproduce-all clean help

install:  ## Install package in editable mode with dev dependencies
	pip install -e ".[dev]"

test:  ## Run unit tests
	pytest tests/ -v

lint:  ## Run ruff linter on compile/ and tests/
	ruff check compile/ tests/

format:  ## Run ruff formatter on compile/ and tests/
	ruff format compile/ tests/

verify:  ## Verify neuron index derivation (requires connectome data)
	python scripts/derive_neuron_indices.py

reproduce-core:  ## Run core experiments (requires connectome data)
	@echo "=== Core experiments ==="
	@echo "Requires: COMPILE_DATA_DIR set or data files in ./data/"
	python experiments/core/edge_sweep.py --fitness navigation
	python experiments/core/bulletproof_evolution.py --fitness navigation --seed 0
	python experiments/core/izh_strategy_switching.py
	python experiments/core/exp6_gene_guided.py
	python experiments/core/exp6_developmental_compiler.py
	python experiments/core/interference_matrix.py
	python experiments/core/expA_prediction.py

reproduce-controls:  ## Run control experiments (requires connectome data)
	@echo "=== Control experiments ==="
	python experiments/controls/critical_controls.py
	python experiments/controls/distraction_control.py
	python experiments/controls/izh_persistence_test.py

reproduce-growth:  ## Run growth experiments (requires connectome data)
	@echo "=== Growth experiments ==="
	python experiments/growth/growth_simulation.py
	python experiments/growth/growth_behavioral_test.py
	python experiments/growth/trajectory_growth.py
	python experiments/growth/axon_trajectory_model.py

reproduce-all: reproduce-core reproduce-controls reproduce-growth  ## Run all experiments
	@echo "=== Cross-species experiments ==="
	python experiments/cross_species/mouse_full_pipeline.py
	@echo "=== Done ==="

clean:  ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/

help:  ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
