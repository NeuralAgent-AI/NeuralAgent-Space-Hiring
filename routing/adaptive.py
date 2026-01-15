"""Adaptive routing implementation.

This is a stub for candidate implementation. Replace this with your adaptive
routing strategy (heuristic or ML-based).

Router Interface:
    get_next_hop(packet, topology, time, history) -> next_hop or None

Args:
    packet: Packet object with attributes:
        - id: Unique packet identifier
        - src: Source node ID
        - dst: Destination node ID
        - current_node: Current node where packet is located
        - ttl_remaining: Time to live remaining (seconds)
        - created_at: Creation timestamp
    
    topology: NetworkX graph representing current network state
        - Nodes: Satellite and ground station IDs
        - Edges: Active links with 'weight' attribute (distance in km)
    
    time: Current simulation time (seconds)
    
    history: List of (time, topology) tuples for recent network states
        - Can be used for topology prediction or learning
        - Empty list if no history available

Returns:
    next_hop: Node ID to route packet to, or None if no route available
        - If None, packet will wait in buffer at current node
        - Must be a neighbor of current_node in topology
"""

import networkx as nx
import random


class AdaptiveRouter:
    """Adaptive router - IMPLEMENT YOUR STRATEGY HERE."""
    
    def __init__(self):
        """Initialize adaptive router."""
        # TODO: Initialize your routing strategy here
        # Examples:
        # - Load ML model
        # - Initialize heuristics
        # - Set up topology prediction
        # - Seed random number generator for reproducibility (if using randomness)
        random.seed(42)  # For reproducibility of random fallback
    
    def get_next_hop(self, packet, topology, time, history):
        """
        Get next hop for packet using adaptive routing strategy.
        
        IMPLEMENT YOUR ADAPTIVE ROUTING LOGIC HERE.
        
        Currently uses a random fallback (picks random neighbor) for testing.
        This performs poorly compared to baseline - replace with your implementation.
        
        Args:
            packet: Packet object with attributes:
                - id: Unique packet identifier
                - src: Source node ID
                - dst: Destination node ID
                - current_node: Current node where packet is located
                - ttl_remaining: Time to live remaining (seconds)
                - created_at: Creation timestamp
            
            topology: NetworkX graph representing current network state
                - Nodes: Satellite and ground station IDs
                - Edges: Active links with 'weight' attribute (distance in km)
            
            time: Current simulation time (seconds)
            
            history: List of (time, topology) tuples for recent network states
                - Can be used for topology prediction or learning
                - Empty list if no history available
        
        Returns:
            next_hop: Node ID to route packet to, or None if no route available
                - If None, packet will wait in buffer at current node
                - Must be a neighbor of current_node in topology
        
        Ideas for adaptive routing:
        - Use topology history to predict link availability
        - Consider TTL remaining when choosing paths
        - Prefer stable links (links that have been up for a while)
        - Use ML to predict best next hop based on features
        - Consider multiple paths and choose based on predicted stability
        - Account for topology changes in the near future
        """
        # TODO: IMPLEMENT YOUR ADAPTIVE ROUTING STRATEGY HERE
        # 
        # Replace the random fallback below with your adaptive routing logic.
        # 
        # Example structure:
        #   1. Check if packet is at destination -> return None
        #   2. Check if destination exists in topology -> return None if not
        #   3. Analyze current topology and history
        #   4. Choose next hop based on your adaptive strategy
        #   5. Return next hop node ID or None
        
        # RANDOM FALLBACK (for testing only - replace with your implementation)
        # This performs poorly and is just to make the code runnable out-of-the-box
        current = packet.current_node
        destination = packet.dst
        
        if current == destination:
            return None
        
        if destination not in topology:
            return None
        
        # Get neighbors of current node
        neighbors = list(topology.neighbors(current))
        if not neighbors:
            return None
        
        # Random fallback: randomly pick a neighbor
        # This will perform poorly compared to baseline shortest path
        # Students should replace this with intelligent routing
        return random.choice(neighbors)
