"""Tests for visibility computation."""

import pytest
import numpy as np
from sim.visibility import VisibilityChecker


def test_isl_range_limit():
    """Test that ISL links respect range limit."""
    checker = VisibilityChecker(isl_range_km=1000, elevation_threshold_deg=5)
    
    # Two satellites within range
    pos1 = np.array([0, 0, 7000])  # 7000 km altitude
    pos2 = np.array([500, 0, 7000])  # 500 km away
    
    assert checker.check_isl(pos1, pos2) == True
    
    # Two satellites beyond range
    pos3 = np.array([0, 0, 7000])
    pos4 = np.array([2000, 0, 7000])  # 2000 km away
    
    assert checker.check_isl(pos3, pos4) == False


def test_ground_link_elevation():
    """Test that ground links respect elevation threshold."""
    checker = VisibilityChecker(isl_range_km=5000, elevation_threshold_deg=10)
    
    # Ground station slightly above Earth surface (on x-axis)
    # R_earth is 6378.137, so place ground at 6380 km
    ground_pos = np.array([6380, 0, 0])  # Slightly above Earth surface at equator
    
    # Satellite directly above (along radius vector) - should have high elevation
    # Unit vector from Earth center to ground: [1, 0, 0]
    # Place satellite 1000 km above along the radius
    sat_pos_high = np.array([7380, 0, 0])  # 1000 km above along radius
    
    assert checker.check_ground_link(sat_pos_high, ground_pos) == True
    
    # Satellite at low elevation (near horizon)
    # Place satellite far horizontally but not much higher vertically
    # Ground at [6380, 0, 0], place satellite at [7000, 4000, 50] for low elevation
    sat_pos_low = np.array([7000, 4000, 50])  # Low elevation angle (mostly horizontal)
    
    # Should fail elevation check (elevation < 10 degrees)
    result = checker.check_ground_link(sat_pos_low, ground_pos)
    assert result == False


def test_earth_occlusion():
    """Test that Earth occlusion is detected."""
    checker = VisibilityChecker()
    
    # Two positions on opposite sides of Earth
    pos1 = np.array([6378, 0, 0])  # On surface
    pos2 = np.array([-6378, 0, 0])  # Opposite side
    
    # Should be occluded
    assert checker._earth_occlusion(pos1, pos2) == True
    
    # Two positions both above Earth
    pos3 = np.array([0, 0, 7000])  # Above north pole
    pos4 = np.array([0, 0, 8000])  # Above north pole, higher
    
    # Should not be occluded
    assert checker._earth_occlusion(pos3, pos4) == False


def test_visibility_matrix():
    """Test visibility matrix computation."""
    checker = VisibilityChecker(isl_range_km=10000, elevation_threshold_deg=5)
    
    positions = {
        'sat1': np.array([0, 0, 7000]),
        'sat2': np.array([1000, 0, 7000]),
        'ground': np.array([6378, 0, 0])
    }
    
    visibility = checker.compute_visibility_matrix(positions)
    
    # Check that matrix is symmetric
    assert visibility[('sat1', 'sat2')] == visibility[('sat2', 'sat1')]
    
    # Check that self-links don't exist (not in matrix)
    assert ('sat1', 'sat1') not in visibility
