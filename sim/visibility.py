"""Line-of-sight and visibility computation for satellite network."""

import numpy as np


class VisibilityChecker:
    """Checks visibility between satellites and ground stations."""
    
    def __init__(self, isl_range_km=5000, elevation_threshold_deg=5):
        """
        Initialize visibility checker.
        
        Args:
            isl_range_km: Maximum inter-satellite link range (km)
            elevation_threshold_deg: Minimum elevation angle for ground links (degrees)
        """
        self.isl_range_km = isl_range_km
        self.elevation_threshold_deg = elevation_threshold_deg
        self.elevation_threshold_rad = np.radians(elevation_threshold_deg)
        
        # Earth radius in km
        self.R_earth = 6378.137
    
    def check_isl(self, pos1, pos2):
        """
        Check if two satellites have line-of-sight.
        
        Args:
            pos1: Position of first satellite (x, y, z) in ECEF (km)
            pos2: Position of second satellite (x, y, z) in ECEF (km)
        
        Returns:
            visible: True if link exists
        """
        # Compute distance
        distance = np.linalg.norm(pos2 - pos1)
        
        # Check range limit
        if distance > self.isl_range_km:
            return False
        
        # Check if line-of-sight is blocked by Earth
        # Simplified: check if line segment intersects Earth sphere
        return not self._earth_occlusion(pos1, pos2)
    
    def check_ground_link(self, sat_pos, ground_pos):
        """
        Check if satellite has visibility to ground station.
        
        Args:
            sat_pos: Satellite position (x, y, z) in ECEF (km)
            ground_pos: Ground station position (x, y, z) in ECEF (km)
        
        Returns:
            visible: True if link exists
        """
        # Compute distance
        distance = np.linalg.norm(sat_pos - ground_pos)
        
        # Compute elevation angle
        # Vector from ground to satellite
        vec = sat_pos - ground_pos
        
        # Unit vector from Earth center to ground station (local "up" direction)
        ground_unit = ground_pos / np.linalg.norm(ground_pos)
        
        # Project satellite vector onto ground unit vector (vertical/radial component)
        vertical_component = np.dot(vec, ground_unit)
        
        # Horizontal component (perpendicular to radius)
        horizontal_vec = vec - vertical_component * ground_unit
        horizontal_component = np.linalg.norm(horizontal_vec)
        
        # Elevation angle: angle above local horizontal plane
        # arctan2(vertical, horizontal) gives elevation from horizon
        elevation = np.arctan2(vertical_component, horizontal_component)
        
        # Check elevation threshold
        if elevation < self.elevation_threshold_rad:
            return False
        
        # Check if line-of-sight is blocked
        return not self._earth_occlusion(ground_pos, sat_pos)
    
    def _earth_occlusion(self, pos1, pos2):
        """
        Check if line segment between pos1 and pos2 is occluded by Earth.
        
        Simplified check: if the minimum distance from Earth center to the line
        interior is less than Earth radius, the link is occluded.
        
        Args:
            pos1: First position (x, y, z) in ECEF (km)
            pos2: Second position (x, y, z) in ECEF (km)
        
        Returns:
            occluded: True if Earth blocks the line-of-sight
        """
        # Vector along the line
        line_vec = pos2 - pos1
        line_length = np.linalg.norm(line_vec)
        
        if line_length < 1e-6:
            return False
        
        # Check distances of endpoints from Earth center
        dist1 = np.linalg.norm(pos1)
        dist2 = np.linalg.norm(pos2)
        
        # If both endpoints are at or above Earth surface, check if line dips below
        if dist1 >= self.R_earth and dist2 >= self.R_earth:
            # For a line from surface outward, it doesn't go through Earth
            # Check if line actually goes through Earth interior
            line_unit = line_vec / line_length
            to_origin = -pos1
            proj = np.dot(to_origin, line_unit)
            
            # The closest point on the infinite line to origin
            # Clamp to segment to check interior
            proj_clamped = np.clip(proj, 0, line_length)
            
            # If minimum is at an endpoint (on or above surface), not occluded
            if abs(proj_clamped) < 1e-6 or abs(proj_clamped - line_length) < 1e-6:
                return False
            
            # Check interior point
            closest_point = pos1 + proj_clamped * line_unit
            min_dist = np.linalg.norm(closest_point)
            
            # Check if interior point is below Earth surface (strictly less)
            return min_dist < self.R_earth - 1e-6
        
        # If one endpoint is below surface, link is occluded
        if dist1 < self.R_earth or dist2 < self.R_earth:
            return True
        
        return False
    
    def compute_visibility_matrix(self, positions):
        """
        Compute visibility matrix for all node pairs.
        
        Args:
            positions: Dict mapping node_id to (x, y, z) position
        
        Returns:
            visibility: Dict of (node1, node2) -> bool
        """
        visibility = {}
        node_ids = list(positions.keys())
        
        for i, node1 in enumerate(node_ids):
            for node2 in node_ids[i+1:]:
                pos1 = positions[node1]
                pos2 = positions[node2]
                
                # Check if both are satellites
                if node1.startswith('sat_') and node2.startswith('sat_'):
                    visible = self.check_isl(pos1, pos2)
                # Check if one is ground station
                elif node1 == 'ground' or node2 == 'ground':
                    if node1 == 'ground':
                        visible = self.check_ground_link(pos2, pos1)
                    else:
                        visible = self.check_ground_link(pos1, pos2)
                else:
                    visible = False
                
                visibility[(node1, node2)] = visible
                visibility[(node2, node1)] = visible
        
        return visibility
