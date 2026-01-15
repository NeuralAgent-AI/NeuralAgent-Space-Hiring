"""Disrupted scenario configuration - reduced connectivity."""

def get_scenario_config():
    """
    Get disrupted scenario configuration.
    
    Returns:
        config: Dict with scenario parameters
    """
    return {
        'name': 'disrupted',
        'isl_range_km': 3000,  # Reduced inter-satellite link range
        'elevation_threshold_deg': 15,  # Higher elevation threshold (stricter)
        'ttl': 120,  # Packet time-to-live (seconds)
        'duration': 600,  # Simulation duration (seconds)
    }
