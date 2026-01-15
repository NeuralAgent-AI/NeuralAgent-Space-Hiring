"""Plot comparison of simulation results."""

import json
import os
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np


def load_results(output_dir='outputs'):
    """Load all result JSON files."""
    results = {}
    output_path = Path(output_dir)
    
    if not output_path.exists():
        print(f"Output directory {output_dir} does not exist.")
        return results
    
    for json_file in output_path.glob('results_*.json'):
        with open(json_file, 'r') as f:
            data = json.load(f)
            scenario = data['scenario']
            router = data['router']
            key = f"{scenario}_{router}"
            results[key] = data
    
    return results


def plot_delivery_rate(results):
    """Plot delivery success rate comparison."""
    scenarios = ['stable', 'disrupted']
    routers = ['baseline', 'adaptive']
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(len(scenarios))
    width = 0.35
    
    baseline_rates = []
    adaptive_rates = []
    
    for scenario in scenarios:
        baseline_key = f"{scenario}_baseline"
        adaptive_key = f"{scenario}_adaptive"
        
        baseline_rate = results.get(baseline_key, {}).get('metrics', {}).get('delivery_rate', 0)
        adaptive_rate = results.get(adaptive_key, {}).get('metrics', {}).get('delivery_rate', 0)
        
        baseline_rates.append(baseline_rate)
        adaptive_rates.append(adaptive_rate)
    
    bars1 = ax.bar(x - width/2, baseline_rates, width, label='Baseline', alpha=0.8)
    bars2 = ax.bar(x + width/2, adaptive_rates, width, label='Adaptive', alpha=0.8)
    
    ax.set_xlabel('Scenario')
    ax.set_ylabel('Delivery Rate')
    ax.set_title('Delivery Success Rate Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios)
    ax.legend()
    ax.set_ylim([0, 1.1])
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2%}',
                   ha='center', va='bottom')
    
    plt.tight_layout()
    return fig


def plot_latency_comparison(results):
    """Plot latency statistics comparison."""
    scenarios = ['stable', 'disrupted']
    routers = ['baseline', 'adaptive']
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    metrics = ['latency_mean', 'latency_median', 'latency_p95']
    metric_labels = ['Mean', 'Median', 'P95']
    
    for idx, scenario in enumerate(scenarios):
        ax = axes[idx]
        
        x = np.arange(len(metric_labels))
        width = 0.35
        
        baseline_values = []
        adaptive_values = []
        
        for metric in metrics:
            baseline_key = f"{scenario}_baseline"
            adaptive_key = f"{scenario}_adaptive"
            
            baseline_val = results.get(baseline_key, {}).get('metrics', {}).get(metric, 0)
            adaptive_val = results.get(adaptive_key, {}).get('metrics', {}).get(metric, 0)
            
            baseline_values.append(baseline_val)
            adaptive_values.append(adaptive_val)
        
        bars1 = ax.bar(x - width/2, baseline_values, width, label='Baseline', alpha=0.8)
        bars2 = ax.bar(x + width/2, adaptive_values, width, label='Adaptive', alpha=0.8)
        
        ax.set_xlabel('Metric')
        ax.set_ylabel('Latency (seconds)')
        ax.set_title(f'Latency Comparison - {scenario.capitalize()} Scenario')
        ax.set_xticks(x)
        ax.set_xticklabels(metric_labels)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{height:.1f}',
                           ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    return fig


def plot_packet_stats(results):
    """Plot packet statistics."""
    scenarios = ['stable', 'disrupted']
    routers = ['baseline', 'adaptive']
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    for idx, scenario in enumerate(scenarios):
        ax = axes[idx]
        
        baseline_key = f"{scenario}_baseline"
        adaptive_key = f"{scenario}_adaptive"
        
        baseline_metrics = results.get(baseline_key, {}).get('metrics', {})
        adaptive_metrics = results.get(adaptive_key, {}).get('metrics', {})
        
        categories = ['Sent', 'Delivered', 'Dropped']
        baseline_values = [
            baseline_metrics.get('total_sent', 0),
            baseline_metrics.get('total_delivered', 0),
            baseline_metrics.get('total_dropped', 0)
        ]
        adaptive_values = [
            adaptive_metrics.get('total_sent', 0),
            adaptive_metrics.get('total_delivered', 0),
            adaptive_metrics.get('total_dropped', 0)
        ]
        
        x = np.arange(len(categories))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, baseline_values, width, label='Baseline', alpha=0.8)
        bars2 = ax.bar(x + width/2, adaptive_values, width, label='Adaptive', alpha=0.8)
        
        ax.set_xlabel('Packet Status')
        ax.set_ylabel('Count')
        ax.set_title(f'Packet Statistics - {scenario.capitalize()} Scenario')
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{int(height)}',
                           ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    return fig


def main():
    """Main plotting function."""
    results = load_results()
    
    if not results:
        print("No results found. Run simulations first.")
        return
    
    print(f"Loaded {len(results)} result files")
    
    # Create plots directory
    plots_dir = Path('outputs') / 'plots'
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate plots
    print("Generating plots...")
    
    fig1 = plot_delivery_rate(results)
    fig1.savefig(plots_dir / 'delivery_rate.png', dpi=150, bbox_inches='tight')
    print(f"Saved: {plots_dir / 'delivery_rate.png'}")
    
    fig2 = plot_latency_comparison(results)
    fig2.savefig(plots_dir / 'latency_comparison.png', dpi=150, bbox_inches='tight')
    print(f"Saved: {plots_dir / 'latency_comparison.png'}")
    
    fig3 = plot_packet_stats(results)
    fig3.savefig(plots_dir / 'packet_stats.png', dpi=150, bbox_inches='tight')
    print(f"Saved: {plots_dir / 'packet_stats.png'}")
    
    print("\nAll plots saved to outputs/plots/")


if __name__ == '__main__':
    main()
