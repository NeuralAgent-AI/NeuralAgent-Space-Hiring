"""Metrics computation for simulation results."""

import numpy as np


class MetricsCollector:
    """Collects and computes simulation metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.packets = []
    
    def add_packet(self, packet):
        """Add packet to metrics collection."""
        self.packets.append(packet)
    
    def compute_metrics(self):
        """
        Compute all metrics from collected packets.
        
        Returns:
            metrics: Dict with computed metrics
        """
        if not self.packets:
            return {
                'total_sent': 0,
                'total_delivered': 0,
                'total_dropped': 0,
                'delivery_rate': 0.0,
                'latency_mean': 0.0,
                'latency_median': 0.0,
                'latency_p95': 0.0,
                'drop_reasons': {}
            }
        
        total_sent = len(self.packets)
        delivered = [p for p in self.packets if p.is_delivered()]
        dropped = [p for p in self.packets if p.is_dropped()]
        
        total_delivered = len(delivered)
        total_dropped = len(dropped)
        
        delivery_rate = total_delivered / total_sent if total_sent > 0 else 0.0
        
        # Compute latencies
        latencies = []
        for p in delivered:
            if p.delivered_at is not None:
                latency = p.delivered_at - p.created_at
                latencies.append(latency)
        
        latency_mean = np.mean(latencies) if latencies else 0.0
        latency_median = np.median(latencies) if latencies else 0.0
        latency_p95 = np.percentile(latencies, 95) if latencies else 0.0
        
        # Count drop reasons
        drop_reasons = {}
        for p in dropped:
            reason = p.drop_reason or 'unknown'
            drop_reasons[reason] = drop_reasons.get(reason, 0) + 1
        
        return {
            'total_sent': total_sent,
            'total_delivered': total_delivered,
            'total_dropped': total_dropped,
            'delivery_rate': float(delivery_rate),
            'latency_mean': float(latency_mean),
            'latency_median': float(latency_median),
            'latency_p95': float(latency_p95),
            'drop_reasons': drop_reasons
        }
