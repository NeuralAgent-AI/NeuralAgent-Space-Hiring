"""Main execution script for satellite network routing simulation."""

import argparse
import json
import os
import sys
from pathlib import Path

from sim.simulator import Simulator
from routing.baseline import BaselineRouter
from routing.adaptive import AdaptiveRouter
from experiments.scenario_stable import get_scenario_config as get_stable_config
from experiments.scenario_disrupted import get_scenario_config as get_disrupted_config


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run satellite network routing simulation'
    )
    parser.add_argument(
        '--scenario',
        type=str,
        choices=['stable', 'disrupted'],
        required=True,
        help='Scenario to run'
    )
    parser.add_argument(
        '--router',
        type=str,
        choices=['baseline', 'adaptive'],
        required=True,
        help='Router to use'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='outputs',
        help='Output directory for results'
    )
    
    args = parser.parse_args()
    
    # Load scenario configuration
    if args.scenario == 'stable':
        scenario_config = get_stable_config()
    else:
        scenario_config = get_disrupted_config()
    
    # Create router
    if args.router == 'baseline':
        router = BaselineRouter()
    else:
        router = AdaptiveRouter()
    
    # Constellation config path
    constellation_config = 'data/constellation.yaml'
    if not os.path.exists(constellation_config):
        print(f"Error: Constellation config not found at {constellation_config}")
        sys.exit(1)
    
    # Create simulator
    simulator = Simulator(
        constellation_config=constellation_config,
        scenario_config=scenario_config,
        router=router
    )
    
    # Run simulation
    print(f"Running simulation: scenario={args.scenario}, router={args.router}")
    print(f"Duration: {scenario_config['duration']} seconds")
    print("Running...")
    
    metrics = simulator.run()
    
    # Print summary
    print("\n" + "="*50)
    print("SIMULATION RESULTS")
    print("="*50)
    print(f"Total packets sent: {metrics['total_sent']}")
    print(f"Total packets delivered: {metrics['total_delivered']}")
    print(f"Total packets dropped: {metrics['total_dropped']}")
    print(f"Delivery rate: {metrics['delivery_rate']:.2%}")
    print(f"\nLatency statistics:")
    print(f"  Mean: {metrics['latency_mean']:.2f} seconds")
    print(f"  Median: {metrics['latency_median']:.2f} seconds")
    print(f"  P95: {metrics['latency_p95']:.2f} seconds")
    if metrics['drop_reasons']:
        print(f"\nDrop reasons:")
        for reason, count in metrics['drop_reasons'].items():
            print(f"  {reason}: {count}")
    print("="*50)
    
    # Save results
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"results_{args.scenario}_{args.router}.json"
    
    # Add metadata to results
    results = {
        'scenario': args.scenario,
        'router': args.router,
        'scenario_config': scenario_config,
        'metrics': metrics
    }
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")


if __name__ == '__main__':
    main()
