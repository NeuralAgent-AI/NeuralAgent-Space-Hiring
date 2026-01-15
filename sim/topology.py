"""Dynamic topology construction from visibility."""

import networkx as nx


class TopologyBuilder:
    """Builds network topology graph from visibility information."""
    
    def __init__(self, visibility_checker):
        """
        Initialize topology builder.
        
        Args:
            visibility_checker: VisibilityChecker instance
        """
        self.visibility_checker = visibility_checker
    
    def build_topology(self, positions):
        """
        Build NetworkX graph from current positions.
        
        Args:
            positions: Dict mapping node_id to (x, y, z) position
        
        Returns:
            G: NetworkX graph with nodes and edges
        """
        G = nx.Graph()
        
        # Add all nodes
        for node_id in positions.keys():
            G.add_node(node_id)
        
        # Compute visibility
        visibility = self.visibility_checker.compute_visibility_matrix(positions)
        
        # Add edges for visible links
        for (node1, node2), visible in visibility.items():
            if visible and node1 < node2:  # Add each edge only once
                # Compute distance for edge weight
                pos1 = positions[node1]
                pos2 = positions[node2]
                distance = ((pos2[0] - pos1[0])**2 + 
                           (pos2[1] - pos1[1])**2 + 
                           (pos2[2] - pos1[2])**2)**0.5
                
                G.add_edge(node1, node2, weight=distance)
        
        return G
