"""Stable scenario configuration - nominal conditions."""

def get_scenario_config():
    """
    Get stable scenario configuration.
    
    Returns:
        config: Dict with scenario parameters
    """
    return {
        'name': 'stable',
        'isl_range_km': 5000,  # Nominal inter-satellite link range
        'elevation_threshold_deg': 5,  # Nominal elevation threshold for ground links
        'ttl': 120,  # Packet time-to-live (seconds)
        'duration': 600,  # Simulation duration (seconds)
    }
