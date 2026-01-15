"""Main simulation loop for satellite network routing."""

from sim.orbit import OrbitPropagator
from sim.visibility import VisibilityChecker
from sim.topology import TopologyBuilder
from sim.traffic import TrafficGenerator
from sim.metrics import MetricsCollector


class Simulator:
    """Main simulator for satellite network routing."""
    
    def __init__(self, constellation_config, scenario_config, router, traffic_config=None):
        """
        Initialize simulator.
        
        Args:
            constellation_config: Path to constellation.yaml
            scenario_config: Scenario configuration dict
            router: Router instance (baseline or adaptive)
            traffic_config: Traffic configuration dict (optional)
        """
        # Initialize components
        self.orbit_prop = OrbitPropagator(constellation_config)
        self.visibility_checker = VisibilityChecker(
            isl_range_km=scenario_config.get('isl_range_km', 5000),
            elevation_threshold_deg=scenario_config.get('elevation_threshold_deg', 5)
        )
        self.topology_builder = TopologyBuilder(self.visibility_checker)
        self.router = router
        
        # Traffic configuration
        if traffic_config is None:
            traffic_config = {
                'period': 5,
                'ttl': scenario_config.get('ttl', 120),
                'src': 'ground',
                'dst': None  # Will be set to first satellite
            }
        
        self.traffic_gen = TrafficGenerator(
            period=traffic_config.get('period', 5),
            ttl=traffic_config.get('ttl', 120),
            src=traffic_config.get('src', 'ground'),
            dst=traffic_config.get('dst')
        )
        
        # Set destination to first satellite if not specified
        if self.traffic_gen.dst is None:
            node_ids = self.orbit_prop.get_node_ids()
            satellites = [n for n in node_ids if n.startswith('sat_')]
            if satellites:
                self.traffic_gen.set_destination(satellites[0])
        
        # Simulation parameters
        self.dt = 1.0  # Timestep (seconds)
        self.duration = scenario_config.get('duration', 600)  # Total duration (seconds)
        
        # Metrics
        self.metrics_collector = MetricsCollector()
        
        # History for adaptive routing (optional)
        self.topology_history = []
    
    def run(self):
        """
        Run the simulation.
        
        Returns:
            metrics: Dict with simulation metrics
        """
        current_time = 0.0
        
        while current_time <= self.duration:
            # 1. Compute satellite positions
            positions = self.orbit_prop.get_positions(current_time)
            
            # 2. Build topology graph
            topology = self.topology_builder.build_topology(positions)
            self.topology_history.append((current_time, topology.copy()))
            
            # 3. Generate new packets
            new_packets = self.traffic_gen.generate_packets(current_time)
            for packet in new_packets:
                self.metrics_collector.add_packet(packet)
            
            # 4. Process all active packets
            all_packets = self.traffic_gen.get_all_packets()
            for packet in all_packets:
                if not packet.is_active():
                    continue
                
                # Check if delivered
                if packet.current_node == packet.dst:
                    packet.delivered_at = current_time
                    continue
                
                # Get next hop from router
                # Pass recent history (last 10 topologies)
                history = self.topology_history[-10:] if len(self.topology_history) > 10 else self.topology_history
                next_hop = self.router.get_next_hop(packet, topology, current_time, history)
                
                if next_hop is not None:
                    # Check if link exists in current topology
                    if topology.has_edge(packet.current_node, next_hop):
                        packet.move_to(next_hop)
                        # Check if delivered after move
                        if packet.current_node == packet.dst:
                            packet.delivered_at = current_time
                            continue
                
                # Decrement TTL
                packet.decrement_ttl(self.dt)
                
                # Check if dropped due to TTL
                if packet.is_dropped():
                    continue
                
                # Check if no path available (optional: mark as dropped)
                # For now, packet waits in buffer
            
            # Advance time
            current_time += self.dt
        
        # Final check: mark packets with no path as dropped
        for packet in all_packets:
            if packet.is_active():
                packet.drop_reason = 'no_path_available'
        
        # Compute and return metrics
        metrics = self.metrics_collector.compute_metrics()
        return metrics
