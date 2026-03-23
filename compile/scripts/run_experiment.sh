#!/bin/bash
# Run the core thesis experiment: Cross-Subject Zero-Shot Transfer
# This validates whether the Latent thesis is real.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ML_DIR="$PROJECT_ROOT/ml"

echo "=============================================="
echo "  LATENT LABS - CORE THESIS EXPERIMENT"
echo "  'Close the bandwidth gap between thought"
echo "   and machine understanding'"
echo "=============================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required"
    exit 1
fi

# Check for virtual environment
if [ ! -d "$ML_DIR/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$ML_DIR/venv"
fi

# Activate virtual environment
source "$ML_DIR/venv/bin/activate"

# Install dependencies
echo "Installing dependencies..."
pip install --quiet torch numpy scikit-learn moabb mne

# Run experiment
echo ""
echo "Running cross-subject zero-shot transfer experiment..."
echo "Dataset: BNCI2014001 (Motor Imagery, 4 classes)"
echo ""

cd "$ML_DIR"
python scripts/run_experiment.py \
    --dataset bnci2014001 \
    --n-classes 4 \
    --epochs 50 \
    --batch-size 32 \
    --output-dir ./results \
    "$@"

echo ""
echo "Experiment complete!"
echo "Results saved to: $ML_DIR/results/"
