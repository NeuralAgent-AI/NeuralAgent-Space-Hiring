"""Orbit propagation for satellite constellation."""

import yaml
import numpy as np


class OrbitPropagator:
    """Propagates satellite orbits using simplified orbital mechanics."""
    
    def __init__(self, constellation_config_path):
        """
        Initialize orbit propagator from constellation configuration.
        
        Args:
            constellation_config_path: Path to constellation.yaml
        """
        with open(constellation_config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        self.constellation = config['constellation']
        self.ground_station = config['ground_station']
        
        # Earth radius in km
        self.R_earth = 6378.137
        
        # Create satellite objects
        self.satellites = self._create_constellation()
        
        # Node ID mapping
        self.node_ids = {}
        node_id = 0
        for plane in range(self.constellation['number_of_planes']):
            for sat in range(self.constellation['sats_per_plane']):
                self.node_ids[(plane, sat)] = f'sat_{plane}_{sat}'
                node_id += 1
        self.node_ids['ground'] = 'ground'
        
        # Reverse mapping
        self.id_to_sat = {v: k for k, v in self.node_ids.items()}
    
    def _create_constellation(self):
        """Create satellite objects for the constellation."""
        satellites = []
        
        # Use a simple circular orbit model
        # For a real implementation, you'd use TLE data or proper orbital elements
        # Here we use a simplified model with mean motion
        
        altitude_km = self.constellation['altitude_km']
        base_inclination_deg = self.constellation['inclination_deg']
        num_planes = self.constellation['number_of_planes']
        
        # Calculate RAAN spacing automatically for even global coverage
        # If raan_spacing_deg is provided, use it; otherwise calculate as 360/num_planes
        if 'raan_spacing_deg' in self.constellation:
            raan_spacing = self.constellation['raan_spacing_deg']
        else:
            # Automatically calculate for even distribution around the globe
            raan_spacing = 360.0 / num_planes
        
        # Calculate different inclinations for each plane with equal spacing
        # Spread inclinations evenly to make them visually distinct
        # Use a range from 30° to 80° with equal spacing between planes
        if num_planes == 1:
            inclinations_deg = [base_inclination_deg]
        else:
            # Equal spacing: for N planes, distribute from min_inc to max_inc
            min_inclination = 30.0  # Minimum inclination (degrees)
            max_inclination = 80.0  # Maximum inclination (degrees)
            inclination_range = max_inclination - min_inclination
            
            inclinations_deg = []
            for plane in range(num_planes):
                if num_planes == 1:
                    inc = base_inclination_deg
                else:
                    # Equal spacing: plane 0 gets min, plane N-1 gets max
                    inc = min_inclination + (inclination_range * plane / (num_planes - 1))
                inclinations_deg.append(inc)
        
        mean_anomaly_spacing = self.constellation['mean_anomaly_spacing_deg']
        
        # Earth radius in km
        R_earth = 6378.137
        # Semi-major axis in km
        a = R_earth + altitude_km
        
        # Store orbital parameters for each satellite
        self.orbital_params = []
        
        for plane in range(num_planes):
            raan = plane * raan_spacing
            plane_inclination_deg = inclinations_deg[plane]
            for sat in range(self.constellation['sats_per_plane']):
                mean_anomaly = sat * mean_anomaly_spacing
                
                params = {
                    'plane': plane,
                    'sat': sat,
                    'a': a,  # km
                    'inclination': np.radians(plane_inclination_deg),
                    'raan': np.radians(raan),
                    'mean_anomaly': np.radians(mean_anomaly),
                }
                self.orbital_params.append(params)
        
        # Store plane inclinations for visualization
        self.plane_inclinations = inclinations_deg
        
        return satellites
    
    def get_positions(self, t):
        """
        Get positions of all satellites and ground station at time t.
        
        Args:
            t: Time in seconds since epoch (simulation start)
        
        Returns:
            positions: Dict mapping node_id to (x, y, z) position in ECEF (km)
        """
        positions = {}
        
        # Get ground station position in ECEF
        lat_rad = np.radians(self.ground_station['lat_deg'])
        lon_rad = np.radians(self.ground_station['lon_deg'])
        alt_km = self.ground_station['alt_m'] / 1000.0
        
        # Earth rotation: longitude changes with time
        # Earth rotation rate (rad/s)
        omega_earth = 7.292115e-5
        lon_rad_at_t = lon_rad + omega_earth * t
        
        # Convert to ECEF
        R = self.R_earth + alt_km
        x = R * np.cos(lat_rad) * np.cos(lon_rad_at_t)
        y = R * np.cos(lat_rad) * np.sin(lon_rad_at_t)
        z = R * np.sin(lat_rad)
        positions['ground'] = np.array([x, y, z])
        
        # Compute satellite positions using simplified orbital mechanics
        for params in self.orbital_params:
            node_id = self.node_ids[(params['plane'], params['sat'])]
            pos = self._compute_satellite_position(params, t)
            positions[node_id] = pos
        
        return positions
    
    def _compute_satellite_position(self, params, t):
        """
        Compute satellite position using simplified orbital mechanics.
        
        Args:
            params: Orbital parameters dict
            t: Time in seconds
        
        Returns:
            position: (x, y, z) in ECEF frame (km)
        """
        a = params['a']  # km
        i = params['inclination']
        raan = params['raan']
        M0 = params['mean_anomaly']
        
        # Earth gravitational parameter (km^3/s^2)
        mu = 398600.4418
        
        # Mean motion (rad/s)
        n = np.sqrt(mu / (a ** 3))
        
        # Mean anomaly at time t
        M = M0 + n * t
        
        # For circular orbits, mean anomaly = true anomaly = eccentric anomaly
        # (simplified model)
        nu = M  # True anomaly
        
        # Position in orbital plane
        r = a
        x_orb = r * np.cos(nu)
        y_orb = r * np.sin(nu)
        z_orb = 0
        
        # Transform to ECI frame
        # Rotation about z-axis by RAAN
        x1 = x_orb * np.cos(raan) - y_orb * np.sin(raan)
        y1 = x_orb * np.sin(raan) + y_orb * np.cos(raan)
        z1 = z_orb
        
        # Rotation about x-axis by inclination
        x2 = x1
        y2 = y1 * np.cos(i) - z1 * np.sin(i)
        z2 = y1 * np.sin(i) + z1 * np.cos(i)
        
        # Transform ECI to ECEF
        # Earth rotation rate (rad/s)
        omega_earth = 7.292115e-5
        # Time since J2000 epoch
        t_since_epoch = t
        theta = omega_earth * t_since_epoch
        
        # Rotate about z-axis by Earth rotation
        x_ecef = x2 * np.cos(theta) - y2 * np.sin(theta)
        y_ecef = x2 * np.sin(theta) + y2 * np.cos(theta)
        z_ecef = z2
        
        return np.array([x_ecef, y_ecef, z_ecef])
    
    def get_node_ids(self):
        """Get list of all node IDs."""
        return list(self.node_ids.values())
