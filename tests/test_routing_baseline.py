"""Tests for baseline routing."""

import pytest
import networkx as nx
from routing.baseline import BaselineRouter
from sim.traffic import Packet


def test_shortest_path_routing():
    """Test that baseline router finds shortest path."""
    router = BaselineRouter()
    
    # Create simple topology: A -> B -> C
    topology = nx.Graph()
    topology.add_edge('A', 'B', weight=1.0)
    topology.add_edge('B', 'C', weight=1.0)
    
    # Create packet from A to C
    packet = Packet(packet_id=0, src='A', dst='C', created_at=0, ttl=100)
    packet.current_node = 'A'
    
    # Should route to B
    next_hop = router.get_next_hop(packet, topology, 0, [])
    assert next_hop == 'B'


def test_no_path():
    """Test that router returns None when no path exists."""
    router = BaselineRouter()
    
    # Create disconnected topology
    topology = nx.Graph()
    topology.add_node('A')
    topology.add_node('B')
    # No edge between A and B
    
    packet = Packet(packet_id=0, src='A', dst='B', created_at=0, ttl=100)
    packet.current_node = 'A'
    
    next_hop = router.get_next_hop(packet, topology, 0, [])
    assert next_hop is None


def test_destination_reached():
    """Test that router returns None when at destination."""
    router = BaselineRouter()
    
    topology = nx.Graph()
    topology.add_node('A')
    
    packet = Packet(packet_id=0, src='A', dst='A', created_at=0, ttl=100)
    packet.current_node = 'A'
    
    next_hop = router.get_next_hop(packet, topology, 0, [])
    assert next_hop is None


def test_weighted_path():
    """Test that router uses edge weights for shortest path."""
    router = BaselineRouter()
    
    # Create topology with two paths: A->B->C (weight 2) and A->D->C (weight 3)
    topology = nx.Graph()
    topology.add_edge('A', 'B', weight=1.0)
    topology.add_edge('B', 'C', weight=1.0)
    topology.add_edge('A', 'D', weight=2.0)
    topology.add_edge('D', 'C', weight=1.0)
    
    packet = Packet(packet_id=0, src='A', dst='C', created_at=0, ttl=100)
    packet.current_node = 'A'
    
    # Should choose A->B->C (shorter)
    next_hop = router.get_next_hop(packet, topology, 0, [])
    assert next_hop == 'B'
