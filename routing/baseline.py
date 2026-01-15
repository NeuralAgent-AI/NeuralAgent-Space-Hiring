"""Baseline shortest-path routing implementation."""

import networkx as nx


class BaselineRouter:
    """Baseline router using shortest path (Dijkstra) on current topology."""
    
    def __init__(self):
        """Initialize baseline router."""
        pass
    
    def get_next_hop(self, packet, topology, time, history):
        """
        Get next hop for packet using shortest path.
        
        Args:
            packet: Packet object with src, dst, current_node, ttl_remaining
            topology: NetworkX graph of current network state
            time: Current simulation time (seconds)
            history: List of (time, topology) tuples (unused in baseline)
        
        Returns:
            next_hop: Node ID to route to, or None if no route available
        """
        current = packet.current_node
        destination = packet.dst
        
        # If already at destination, return None
        if current == destination:
            return None
        
        # Check if destination is in topology
        if destination not in topology:
            return None
        
        # Try to find shortest path
        try:
            path = nx.shortest_path(topology, current, destination, weight='weight')
            if len(path) > 1:
                return path[1]  # Next hop is second node in path
        except nx.NetworkXNoPath:
            # No path exists
            return None
        
        return None
