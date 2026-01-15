# CASAS Routing Challenge

A satellite network routing assignment for evaluating coding ability, networking fundamentals, space/orbital reasoning, and engineering judgment.

## Overview

This project provides a working satellite network simulator where you implement an adaptive routing strategy. The simulator handles orbital mechanics, visibility computation, and dynamic topology changes. Your task is to implement routing logic that adapts to the changing network topology.

### Key Features

- **Deterministic Simulation**: Orbital mechanics and topology changes are deterministic based on geometry
- **Dynamic Topology**: Links appear and disappear based on satellite visibility
- **Traffic Generation**: Periodic packet generation with configurable patterns
- **Baseline Routing**: Shortest-path routing provided as a baseline
- **Two Scenarios**: Stable (nominal conditions) and Disrupted (reduced connectivity)

## Setup

### Requirements

- Python 3.10 or higher
- pip

### Installation

```bash
pip install -r requirements.txt
```

## Running the Simulator

### Basic Usage

Run a simulation with a specific scenario and router:

```bash
python run.py --scenario stable --router baseline
python run.py --scenario stable --router adaptive
python run.py --scenario disrupted --router baseline
python run.py --scenario disrupted --router adaptive
```

### Output

Each run generates a results file in `outputs/`:
- `outputs/results_stable_baseline.json`
- `outputs/results_stable_adaptive.json`
- `outputs/results_disrupted_baseline.json`
- `outputs/results_disrupted_adaptive.json`

### Visualization

Generate comparison plots from all results:

```bash
python plots/plot_results.py
```

Plots are saved to `outputs/plots/`.

## Testing

Run the test suite:

```bash
python -m pytest
```

## Project Structure

```
casas-routing-challenge/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── run.py                    # Main execution script
├── report_template.md        # Template for your report
├── model_card_template.md    # Template for ML model documentation
├── data/
│   └── constellation.yaml    # Constellation parameters (DO NOT MODIFY)
├── sim/                      # Core simulation components
│   ├── orbit.py              # Orbit propagation
│   ├── visibility.py         # Line-of-sight computation
│   ├── topology.py           # Dynamic graph construction
│   ├── traffic.py            # Packet generation
│   ├── metrics.py            # Metrics computation
│   └── simulator.py          # Main simulation loop
├── routing/                  # Routing implementations
│   ├── baseline.py           # Baseline shortest-path router
│   └── adaptive.py           # YOUR IMPLEMENTATION HERE
├── experiments/              # Scenario configurations
│   ├── scenario_stable.py
│   └── scenario_disrupted.py
├── plots/                    # Visualization scripts
│   └── plot_results.py
├── outputs/                  # Results and plots
│   └── .gitkeep
└── tests/                    # Test suite
    ├── test_visibility.py
    └── test_routing_baseline.py
```

## Your Task

### Implementation

Implement your adaptive routing strategy in `routing/adaptive.py`. The file contains a stub with the expected interface.

**Important Note**: Currently, `adaptive.py` uses a fallback to baseline shortest-path routing, so initial results will be identical to baseline. You must implement your adaptive strategy to see performance differences.

**Router Interface:**
```python
def get_next_hop(self, packet, topology, time, history):
    """
    Args:
        packet: Packet object with src, dst, current_node, ttl_remaining
        topology: NetworkX graph of current network state
        time: Current simulation time (seconds)
        history: List of previous topology states (optional)
    
    Returns:
        next_hop: Node ID to route to, or None if no route available
    """
```

### Approach Options

You may implement either:
1. **Heuristic-based routing**: Use graph properties, topology predictions, or other heuristics
2. **ML-based routing**: Use scikit-learn or small PyTorch models (see constraints below)

### ML Constraints (if using ML)

- Training must complete on CPU in < 2-3 minutes
- No GPUs required
- No long RL training loops
- Must include fallback to baseline if inference fails
- Document in `model_card.md`:
  - Features used
  - Model type
  - Training data source
  - Inference cost estimate

**Allowed ML libraries:**
- scikit-learn
- torch (small models only)

**Disallowed:**
- Large RL frameworks
- Distributed training
- AutoML
- Black-box simulators

### Deliverables

1. **Implementation**: Complete `routing/adaptive.py`
2. **Results**: Run all four combinations (stable/disrupted × baseline/adaptive) with default constellation
3. **Constellation Scaling Analysis** (REQUIRED): Test your routing with different network sizes
4. **Report**: Fill out `report_template.md` with:
   - Your routing idea
   - Features/state used
   - When it helps vs. when it fails
   - Scaling analysis results
5. **Model Card** (if using ML): Fill out `model_card_template.md`

### Constellation Scaling Analysis (REQUIRED)

**You must test your routing strategy with different constellation sizes to analyze scalability.**

The default configuration starts with **4 planes × 4 satellites = 16 satellites** (plus ground station = 17 nodes).

**Required Steps:**

1. **Test with default configuration (4×4)**:
   ```bash
   python run.py --scenario stable --router adaptive
   ```

2. **Test with progressively larger constellations**:
   Modify `data/constellation.yaml` and test at least 3 different sizes:
   - **Small**: 4 planes × 4 sats = 16 satellites (default)
   - **Medium**: 6 planes × 6 sats = 36 satellites
   - **Large**: 8 planes × 8 sats = 64 satellites
   - **Optional**: Test even larger (e.g., 10×10 = 100 satellites)

   Keep other parameters (altitude, inclination) the same for fair comparison.

3. **For each configuration, run**:
   ```bash
   python run.py --scenario stable --router adaptive
   python run.py --scenario stable --router baseline  # For comparison
   ```

4. **Analyze and document**:
   - How does **delivery rate** change with network size?
   - How does **latency** change (mean, median, p95)?
   - How does **computation time** scale? (Does routing get slower?)
   - Does your routing strategy scale well, or does performance degrade?
   - At what point does the network become too dense/sparse?
   - What are the trade-offs between more satellites vs. better routing?
   - Compare your adaptive router vs. baseline at each size

5. **Include findings in report**: Document results in the "Constellation Scaling Analysis" section of your report.

## How It Works

### Simulation Model

- **Time**: Discrete timesteps of 1 second, total duration 600 seconds
- **Packets**: Store-and-forward, one hop per timestep
- **Topology**: Rebuilt every timestep from current satellite positions
- **Packet Loss**: Occurs due to TTL expiration or no available path (not randomness)

### Packet Structure

Each packet has:
- `id`: Unique identifier
- `src`, `dst`: Source and destination nodes
- `created_at`: Creation timestamp
- `current_node`: Current location
- `ttl_remaining`: Time to live remaining (seconds)
- `delivered_at`: Delivery timestamp (if delivered)
- `drop_reason`: Reason for drop (if dropped)

### Metrics

The simulator computes:
- Total packets sent
- Total packets delivered
- Delivery success rate
- Latency statistics (mean, median, p95)
- Drop reasons count

## Constraints

- **Core task**: Only modify `routing/adaptive.py` and optionally add helper files under `routing/`
- **Scaling analysis**: You MUST modify `data/constellation.yaml` to test different network sizes (see Constellation Scaling Analysis above)
- **DO NOT modify**: Orbital mechanics code (`sim/orbit.py`) or other core simulation components
- **Deterministic**: All behavior must be deterministic (seed randomness if used)

**Note**: Start with the default constellation (4×4) for your main routing implementation, then test with larger sizes for the required scaling analysis.

## Evaluation Criteria

We evaluate:
1. **Coding ability**: Clean, readable code in an existing codebase
2. **Networking fundamentals**: Understanding of routing, latency, packet loss
3. **Space/orbital reasoning**: Handling contact-driven topology dynamics
4. **Engineering judgment**: Appropriate use of heuristics vs. ML, simplicity vs. overengineering

## Questions?

Review the codebase to understand the simulation model. The baseline router provides a reference implementation.

Good luck!
