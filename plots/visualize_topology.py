"""Visualize satellite constellation topology and routing paths."""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import networkx as nx
import yaml
import random
import hashlib

# Try to import Cartopy for map projections (preferred)
try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    from cartopy.mpl.geoaxes import GeoAxes
    HAS_CARTOPY = True
except ImportError:
    HAS_CARTOPY = False

# Try to import Basemap for map projections (fallback, deprecated)
try:
    from mpl_toolkits.basemap import Basemap
    HAS_BASEMAP = True
except ImportError:
    HAS_BASEMAP = False

from sim.orbit import OrbitPropagator
from sim.visibility import VisibilityChecker
from sim.topology import TopologyBuilder
from routing.baseline import BaselineRouter
from routing.adaptive import AdaptiveRouter
from sim.traffic import Packet
from sim.simulator import Simulator
from experiments.scenario_stable import get_scenario_config as get_stable_config
import json


def plot_constellation_3d(positions, topology, packet_path=None, time=0, orbit_prop=None):
    """
    Plot 3D visualization of constellation with topology, orbital planes, and routing path.
    
    Args:
        positions: Dict mapping node_id to (x, y, z) position
        topology: NetworkX graph
        packet_path: List of node IDs representing a routing path (optional)
        time: Current time for title
        orbit_prop: OrbitPropagator instance for orbital plane visualization
    """
    fig = plt.figure(figsize=(20, 16))
    
    # 3D plot with Earth and orbital planes
    ax = fig.add_subplot(221, projection='3d')
    
    # Extract positions
    node_positions = {}
    for node_id, pos in positions.items():
        node_positions[node_id] = pos
    
    R_earth = 6378.137
    
    # Plot Earth (sphere) - more visible
    u = np.linspace(0, 2 * np.pi, 30)
    v = np.linspace(0, np.pi, 30)
    x_earth = R_earth * np.outer(np.cos(u), np.sin(v))
    y_earth = R_earth * np.outer(np.sin(u), np.sin(v))
    z_earth = R_earth * np.outer(np.ones(np.size(u)), np.cos(v))
    ax.plot_surface(x_earth, y_earth, z_earth, alpha=0.3, color='lightblue', 
                   edgecolor='blue', linewidth=0.5)
    
    # Plot orbital planes if orbit_prop is provided
    if orbit_prop is not None:
        altitude_km = orbit_prop.constellation['altitude_km']
        inclination_deg = orbit_prop.constellation['inclination_deg']
        num_planes = orbit_prop.constellation['number_of_planes']
        # Calculate RAAN spacing (auto-calculated if not in config)
        if 'raan_spacing_deg' in orbit_prop.constellation:
            raan_spacing = orbit_prop.constellation['raan_spacing_deg']
        else:
            raan_spacing = 360.0 / num_planes
        
        R_orbit = R_earth + altitude_km
        
        # Color scheme for different planes
        plane_colors_orbits = ['red', 'orange', 'yellow', 'lime', 'cyan', 'magenta']
        
        # Draw orbital plane surfaces and circles for each plane
        for plane in range(num_planes):
            raan = np.radians(plane * raan_spacing)
            inclination = np.radians(inclination_deg)
            plane_color = plane_colors_orbits[plane % len(plane_colors_orbits)]
            
            # Generate points along the orbital circle
            nu = np.linspace(0, 2 * np.pi, 100)
            r = R_orbit
            
            # Position in orbital plane
            x_orb = r * np.cos(nu)
            y_orb = r * np.sin(nu)
            z_orb = np.zeros_like(nu)
            
            # Transform to ECI frame (RAAN rotation)
            x1 = x_orb * np.cos(raan) - y_orb * np.sin(raan)
            y1 = x_orb * np.sin(raan) + y_orb * np.cos(raan)
            z1 = z_orb
            
            # Transform to ECI frame (inclination rotation)
            x2 = x1
            y2 = y1 * np.cos(inclination) - z1 * np.sin(inclination)
            z2 = y1 * np.sin(inclination) + z1 * np.cos(inclination)
            
            # Transform ECI to ECEF (Earth rotation at time t)
            omega_earth = 7.292115e-5
            theta = omega_earth * time
            x_ecef = x2 * np.cos(theta) - y2 * np.sin(theta)
            y_ecef = x2 * np.sin(theta) + y2 * np.cos(theta)
            z_ecef = z2
            
            # Plot orbital plane circle (thicker, more visible)
            ax.plot(x_ecef, y_ecef, z_ecef, 
                   color=plane_color, alpha=0.6, linewidth=3, linestyle='-',
                   label=f'Plane {plane} Orbit' if plane < 4 else '')
            
            # Add direction arrows along the orbit (showing satellite movement direction)
            # Sample a few points along the orbit for arrows
            num_arrows = 12
            arrow_indices = np.linspace(0, len(nu)-2, num_arrows, dtype=int)
            for idx in arrow_indices:
                if idx < len(nu) - 1:
                    # Current position
                    p1 = np.array([x_ecef[idx], y_ecef[idx], z_ecef[idx]])
                    # Next position (for direction)
                    p2 = np.array([x_ecef[idx+1], y_ecef[idx+1], z_ecef[idx+1]])
                    # Direction vector
                    direction = p2 - p1
                    norm = np.linalg.norm(direction)
                    if norm > 1e-6:  # Avoid division by zero
                        direction = direction / norm * 300  # Scale arrow
                        
                        # Draw arrow using quiver
                        try:
                            ax.quiver(p1[0], p1[1], p1[2], 
                                    direction[0], direction[1], direction[2],
                                    color=plane_color, alpha=0.7, 
                                    arrow_length_ratio=0.2, linewidth=2, length=300)
                        except:
                            # Fallback: draw simple line if quiver fails
                            ax.plot([p1[0], p1[0] + direction[0]], 
                                  [p1[1], p1[1] + direction[1]], 
                                  [p1[2], p1[2] + direction[2]], 
                                  color=plane_color, alpha=0.7, linewidth=2)
    
    # Plot links (edges)
    for edge in topology.edges():
        node1, node2 = edge
        if node1 in node_positions and node2 in node_positions:
            pos1 = node_positions[node1]
            pos2 = node_positions[node2]
            ax.plot([pos1[0], pos2[0]], 
                   [pos1[1], pos2[1]], 
                   [pos1[2], pos2[2]], 
                   'gray', alpha=0.3, linewidth=0.5)
    
    # Plot routing path if provided
    if packet_path and len(packet_path) > 1:
        for i in range(len(packet_path) - 1):
            node1 = packet_path[i]
            node2 = packet_path[i + 1]
            if node1 in node_positions and node2 in node_positions:
                pos1 = node_positions[node1]
                pos2 = node_positions[node2]
                ax.plot([pos1[0], pos2[0]], 
                       [pos1[1], pos2[1]], 
                       [pos1[2], pos2[2]], 
                       'red', linewidth=3, alpha=0.8, label='Routing Path' if i == 0 else '')
    
    # Plot satellites with plane-based coloring
    sat_positions = []
    plane_colors = ['orange', 'yellow', 'lime', 'magenta', 'cyan', 'pink']
    
    def get_plane_from_id(node_id):
        """Extract plane number from satellite ID"""
        if node_id.startswith('sat_'):
            parts = node_id.split('_')
            if len(parts) >= 2:
                try:
                    return int(parts[1])
                except ValueError:
                    return 0
        return 0
    
    for node_id, pos in node_positions.items():
        if node_id.startswith('sat_'):
            sat_positions.append(pos)
            plane = get_plane_from_id(node_id)
            color = plane_colors[plane % len(plane_colors)]
            ax.scatter(pos[0], pos[1], pos[2], c=color, s=80, alpha=0.9, 
                      edgecolors='black', linewidths=0.5)
    
    # Plot ground station
    if 'ground' in node_positions:
        gs_pos = node_positions['ground']
        ax.scatter(gs_pos[0], gs_pos[1], gs_pos[2], c='green', s=200, 
                  marker='^', label='Ground Station', alpha=0.9)
    
    # Highlight source and destination if path provided
    if packet_path:
        if packet_path[0] in node_positions:
            src_pos = node_positions[packet_path[0]]
            ax.scatter(src_pos[0], src_pos[1], src_pos[2], c='blue', s=300, 
                      marker='s', label='Source', edgecolors='black', linewidths=2)
        if packet_path[-1] in node_positions:
            dst_pos = node_positions[packet_path[-1]]
            ax.scatter(dst_pos[0], dst_pos[1], dst_pos[2], c='red', s=300, 
                      marker='*', label='Destination', edgecolors='black', linewidths=2)
    
    ax.set_xlabel('X (km)')
    ax.set_ylabel('Y (km)')
    ax.set_zlabel('Z (km)')
    ax.set_title(f'3D Constellation with Orbital Planes (t={time}s)', fontsize=12, fontweight='bold')
    
    # Set equal aspect ratio for better visualization
    max_range = 8000
    ax.set_xlim([-max_range, max_range])
    ax.set_ylim([-max_range, max_range])
    ax.set_zlim([-max_range, max_range])
    
    # Limit legend to avoid clutter
    handles, labels = ax.get_legend_handles_labels()
    # Keep only unique labels
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='upper left', fontsize=8)
    
    # 2D projection (XY plane)
    ax2 = fig.add_subplot(222)
    
    # Plot Earth circle
    circle = plt.Circle((0, 0), R_earth, fill=True, facecolor='lightblue', alpha=0.2, edgecolor='blue', linewidth=1)
    ax2.add_patch(circle)
    
    # Plot orbital plane projections if orbit_prop is provided
    if orbit_prop is not None:
        altitude_km = orbit_prop.constellation['altitude_km']
        num_planes = orbit_prop.constellation['number_of_planes']
        # Calculate RAAN spacing (auto-calculated if not in config)
        if 'raan_spacing_deg' in orbit_prop.constellation:
            raan_spacing = orbit_prop.constellation['raan_spacing_deg']
        else:
            raan_spacing = 360.0 / num_planes
        R_orbit = R_earth + altitude_km
        
        # Draw orbital plane circles (projected to XY plane)
        for plane in range(num_planes):
            raan = np.radians(plane * raan_spacing)
            # Generate points along the orbital circle
            nu = np.linspace(0, 2 * np.pi, 100)
            r = R_orbit
            
            # Position in orbital plane (simplified projection)
            x_orb = r * np.cos(nu)
            y_orb = r * np.sin(nu)
            
            # Rotate by RAAN
            x_rot = x_orb * np.cos(raan) - y_orb * np.sin(raan)
            y_rot = x_orb * np.sin(raan) + y_orb * np.cos(raan)
            
            # Transform ECI to ECEF (Earth rotation at time t)
            omega_earth = 7.292115e-5
            theta = omega_earth * time
            x_ecef = x_rot * np.cos(theta) - y_rot * np.sin(theta)
            y_ecef = x_rot * np.sin(theta) + y_rot * np.cos(theta)
            
            # Plot orbital plane projection
            ax2.plot(x_ecef, y_ecef, color='cyan', alpha=0.3, linewidth=1, 
                    linestyle='--', label=f'Plane {plane}' if plane < 3 else '')
    
    # Plot links
    for edge in topology.edges():
        node1, node2 = edge
        if node1 in node_positions and node2 in node_positions:
            pos1 = node_positions[node1]
            pos2 = node_positions[node2]
            ax2.plot([pos1[0], pos2[0]], [pos1[1], pos2[1]], 
                     'gray', alpha=0.2, linewidth=0.5)
    
    # Plot routing path
    if packet_path and len(packet_path) > 1:
        for i in range(len(packet_path) - 1):
            node1 = packet_path[i]
            node2 = packet_path[i + 1]
            if node1 in node_positions and node2 in node_positions:
                pos1 = node_positions[node1]
                pos2 = node_positions[node2]
                ax2.plot([pos1[0], pos2[0]], [pos1[1], pos2[1]], 
                        'red', linewidth=2, alpha=0.8, label='Path' if i == 0 else '')
    
    # Plot nodes
    for node_id, pos in node_positions.items():
        if node_id.startswith('sat_'):
            ax2.scatter(pos[0], pos[1], c='orange', s=30, alpha=0.6)
        elif node_id == 'ground':
            ax2.scatter(pos[0], pos[1], c='green', s=200, marker='^', 
                       label='Ground Station', alpha=0.9)
    
    # Highlight source and destination
    if packet_path:
        if packet_path[0] in node_positions:
            src_pos = node_positions[packet_path[0]]
            ax2.scatter(src_pos[0], src_pos[1], c='blue', s=300, marker='s', 
                       label='Source', edgecolors='black', linewidths=2)
        if packet_path[-1] in node_positions:
            dst_pos = node_positions[packet_path[-1]]
            ax2.scatter(dst_pos[0], dst_pos[1], c='red', s=300, marker='*', 
                       label='Destination', edgecolors='black', linewidths=2)
    
    ax2.set_xlabel('X (km)')
    ax2.set_ylabel('Y (km)')
    ax2.set_title('Top View (XY Projection)')
    ax2.set_aspect('equal')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Network graph visualization
    ax4 = fig.add_subplot(224)
    
    # Create layout for network graph
    pos_graph = {}
    for node_id, pos in node_positions.items():
        # Use 2D projection for layout
        pos_graph[node_id] = (pos[0], pos[1])
    
    # Draw network
    nx.draw_networkx_edges(topology, pos_graph, ax=ax4, alpha=0.3, width=0.5, edge_color='gray')
    
    # Draw routing path
    if packet_path and len(packet_path) > 1:
        path_edges = [(packet_path[i], packet_path[i+1]) for i in range(len(packet_path)-1)]
        nx.draw_networkx_edges(topology, pos_graph, edgelist=path_edges, 
                              ax=ax4, edge_color='red', width=3, alpha=0.8)
    
    # Draw nodes
    sat_nodes = [n for n in topology.nodes() if n.startswith('sat_')]
    ground_nodes = [n for n in topology.nodes() if n == 'ground']
    
    if sat_nodes:
        nx.draw_networkx_nodes(topology, pos_graph, nodelist=sat_nodes, 
                              ax=ax4, node_color='orange', node_size=100, alpha=0.7)
    
    if ground_nodes:
        nx.draw_networkx_nodes(topology, pos_graph, nodelist=ground_nodes, 
                              ax=ax4, node_color='green', node_size=500, 
                              node_shape='^', alpha=0.9)
    
    # Highlight source and destination
    if packet_path:
        if packet_path[0] in topology.nodes():
            nx.draw_networkx_nodes(topology, pos_graph, nodelist=[packet_path[0]], 
                                  ax=ax4, node_color='blue', node_size=800, 
                                  node_shape='s', alpha=0.9)
        if packet_path[-1] in topology.nodes():
            nx.draw_networkx_nodes(topology, pos_graph, nodelist=[packet_path[-1]], 
                                  ax=ax4, node_color='red', node_size=800, 
                                  node_shape='*', alpha=0.9)
    
    ax4.set_title('Network Graph View', fontsize=11, fontweight='bold')
    ax4.axis('off')
    
    # Statistics
    ax4 = fig.add_subplot(224)
    ax4.axis('off')
    
    stats_text = f"""
    Network Statistics (t={time}s):
    
    Total Nodes: {len(topology.nodes())}
    Total Edges: {len(topology.edges())}
    Satellites: {len([n for n in topology.nodes() if n.startswith('sat_')])}
    Ground Stations: {len([n for n in topology.nodes() if n == 'ground'])}
    
    Connectivity:
    - Average Degree: {2*len(topology.edges())/len(topology.nodes()):.2f}
    - Is Connected: {nx.is_connected(topology)}
    
    Routing Path:
    """
    
    if packet_path:
        stats_text += f"""
    - Source: {packet_path[0]}
    - Destination: {packet_path[-1]}
    - Path Length: {len(packet_path)-1} hops
    - Path: {' -> '.join(packet_path[:5])}{'...' if len(packet_path) > 5 else ''}
    """
    else:
        stats_text += "\n    No path shown"
    
    ax4.text(0.1, 0.5, stats_text, fontsize=11, family='monospace',
            verticalalignment='center', transform=ax4.transAxes)
    
    plt.tight_layout()
    return fig


def ecef_to_latlon(pos_ecef):
    """
    Convert ECEF coordinates to latitude and longitude.
    
    Args:
        pos_ecef: (x, y, z) position in ECEF frame (km)
    
    Returns:
        (lat_deg, lon_deg): Latitude and longitude in degrees
    """
    x, y, z = pos_ecef
    R = np.linalg.norm(pos_ecef)
    
    # Latitude (angle from equatorial plane)
    lat_rad = np.arcsin(z / R)
    lat_deg = np.degrees(lat_rad)
    
    # Longitude (angle in equatorial plane)
    lon_rad = np.arctan2(y, x)
    lon_deg = np.degrees(lon_rad)
    
    return lat_deg, lon_deg


def plot_sinusoidal_2d_routing(positions, topology, orbit_prop, packet_path=None, title_suffix=""):
    """
    Plot 2D world map with open-source map showing satellite ground tracks and routing paths.
    Uses Cartopy for proper world map visualization.
    
    Args:
        positions: Dict mapping node_id to (x, y, z) position
        topology: NetworkX graph
        orbit_prop: OrbitPropagator instance
        packet_path: Optional routing path to highlight
        title_suffix: Additional text for title
    """
    # Use Cartopy if available, otherwise fall back to simple projection
    if HAS_CARTOPY:
        # Use PlateCarree (equirectangular) projection for world map
        fig = plt.figure(figsize=(20, 10))
        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.set_global()
        
        # Add map features
        ax.add_feature(cfeature.LAND, facecolor='#d4c5a9', alpha=0.7, zorder=0)
        ax.add_feature(cfeature.OCEAN, facecolor='#a8d5e2', alpha=0.7, zorder=0)
        ax.add_feature(cfeature.COASTLINE, linewidth=0.8, zorder=1)
        ax.add_feature(cfeature.BORDERS, linewidth=0.5, linestyle='--', alpha=0.5, zorder=1)
        ax.add_feature(cfeature.LAKES, facecolor='#a8d5e2', alpha=0.5, zorder=0)
        
        # Add gridlines
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, linewidth=0.5, 
                         color='gray', alpha=0.5, linestyle='--', zorder=2)
        gl.top_labels = False
        gl.right_labels = False
        gl.xlabel_style = {'size': 9}
        gl.ylabel_style = {'size': 9}
        
        use_cartopy = True
    else:
        # Fallback: simple matplotlib plot
        fig, ax = plt.subplots(figsize=(20, 10))
        use_cartopy = False
        
        # Add simple continent shapes
        # North America
        na_lons = np.array([-170, -100, -80, -70, -60, -50, -170])
        na_lats = np.array([60, 60, 45, 35, 50, 70, 60])
        na_x = na_lons * np.cos(np.radians(na_lats))
        ax.fill(na_x, na_lats, color='#d4c5a9', alpha=0.7, zorder=0, edgecolor='#8b7355', linewidth=0.5)
        
        # South America
        sa_lons = np.array([-80, -35, -30, -40, -80])
        sa_lats = np.array([10, 10, -35, -55, 10])
        sa_x = sa_lons * np.cos(np.radians(sa_lats))
        ax.fill(sa_x, sa_lats, color='#d4c5a9', alpha=0.7, zorder=0, edgecolor='#8b7355', linewidth=0.5)
        
        # Europe/Africa
        eaf_lons = np.array([-10, 40, 50, 30, -10])
        eaf_lats = np.array([70, 70, -35, -35, 70])
        eaf_x = eaf_lons * np.cos(np.radians(eaf_lats))
        ax.fill(eaf_x, eaf_lats, color='#d4c5a9', alpha=0.7, zorder=0, edgecolor='#8b7355', linewidth=0.5)
        
        # Asia
        asia_lons = np.array([50, 150, 180, 50])
        asia_lats = np.array([70, 70, 50, 70])
        asia_x = asia_lons * np.cos(np.radians(asia_lats))
        ax.fill(asia_x, asia_lats, color='#d4c5a9', alpha=0.7, zorder=0, edgecolor='#8b7355', linewidth=0.5)
        
        # Australia
        aus_lons = np.array([110, 155, 155, 110])
        aus_lats = np.array([-10, -10, -45, -45])
        aus_x = aus_lons * np.cos(np.radians(aus_lats))
        ax.fill(aus_x, aus_lats, color='#d4c5a9', alpha=0.7, zorder=0, edgecolor='#8b7355', linewidth=0.5)
        
        # Grid lines
        for lat_line in range(-90, 91, 30):
            ax.axhline(y=lat_line, color='gray', linewidth=0.5, alpha=0.3, linestyle=':', zorder=0)
        for lon_line in range(-180, 181, 30):
            x_line = lon_line * np.cos(np.radians(0))
            ax.axvline(x=x_line, color='gray', linewidth=0.5, alpha=0.3, linestyle=':', zorder=0)
        
        ax.set_facecolor('#a8d5e2')  # Light blue ocean
        ax.set_xlim([-200, 200])
        ax.set_ylim([-90, 90])
    
    # Helper function to get plane from node ID
    def get_plane_from_id(node_id):
        if node_id.startswith('sat_'):
            parts = node_id.split('_')
            if len(parts) >= 2:
                try:
                    return int(parts[1])
                except ValueError:
                    return 0
        return -1  # Ground station
    
    # Get constellation info
    num_planes = orbit_prop.constellation['number_of_planes'] if orbit_prop else 0
    sats_per_plane = orbit_prop.constellation['sats_per_plane'] if orbit_prop else 0
    total_sats = num_planes * sats_per_plane
    
    # Generate and plot orbital paths (ground tracks) for each satellite
    # This helps students understand how satellites move in their orbits
    plane_colors = ['magenta', 'purple', 'violet', 'fuchsia', 'mediumorchid', 'darkviolet', 'blueviolet', 'indigo']
    
    # Generate ground tracks for satellites to show their orbital paths
    # Show one satellite per plane to demonstrate orbital patterns without clutter
    duration_minutes = 90  # Show ~1.5 orbits (LEO period ~90-100 minutes)
    num_points = 200
    time_points = np.linspace(0, duration_minutes * 60, num_points)
    
    # Get one satellite per plane for track visualization
    node_ids = orbit_prop.get_node_ids() if orbit_prop else []
    satellites_by_plane = {}
    for node_id in node_ids:
        if node_id.startswith('sat_'):
            plane = get_plane_from_id(node_id)
            if plane not in satellites_by_plane:
                satellites_by_plane[plane] = node_id
    
    # Plot ground tracks for one satellite per plane
    for plane, sat_id in satellites_by_plane.items():
        plane_color = plane_colors[plane % len(plane_colors)]
        
        lats = []
        lons = []
        
        for t in time_points:
            pos = orbit_prop.get_positions(t)[sat_id]
            lat, lon = ecef_to_latlon(pos)
            lats.append(lat)
            lons.append(lon)
        
        if lats and lons:
            lons = np.array(lons)
            lats = np.array(lats)
            
            # Unwrap longitude to avoid jumps
            lons_unwrapped = np.unwrap(np.radians(lons))
            lons_unwrapped = np.degrees(lons_unwrapped)
            
            # Plot orbital path (ground track) - subtle but visible
            if use_cartopy:
                ax.plot(lons_unwrapped, lats, color=plane_color, linewidth=1.0, alpha=0.4, 
                       transform=ccrs.PlateCarree(), zorder=2,
                       label=f'Plane {plane} Orbit' if plane == 0 else '')
            else:
                x_track = lons_unwrapped * np.cos(np.radians(lats))
                y_track = lats
                ax.plot(x_track, y_track, color=plane_color, linewidth=1.0, alpha=0.4, 
                       zorder=2, label=f'Plane {plane} Orbit' if plane == 0 else '')
    
    # Plot current satellite positions with labels (like reference image)
    node_latlon = {}
    for node_id, pos in positions.items():
        lat, lon = ecef_to_latlon(pos)
        node_latlon[node_id] = (lat, lon)
        
        if node_id.startswith('sat_'):
            plane = get_plane_from_id(node_id)
            plane_color = plane_colors[plane % len(plane_colors)]
            
            # Plot satellite
            if use_cartopy:
                ax.scatter(lon, lat, c=plane_color, s=80, alpha=0.9, 
                          edgecolors='black', linewidths=1, zorder=10,
                          transform=ccrs.PlateCarree())
                # Add label
                label_text = node_id.replace('sat_', 'Sat_')
                ax.text(lon, lat + 2, label_text, fontsize=7, ha='center', 
                       color='black', fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                               edgecolor='black', alpha=0.9, linewidth=0.5),
                       transform=ccrs.PlateCarree(), zorder=15)
            else:
                # Sinusoidal projection
                x = lon * np.cos(np.radians(lat))
                y = lat
                ax.scatter(x, y, c=plane_color, s=80, alpha=0.9, 
                          edgecolors='black', linewidths=1, zorder=10)
                # Add label
                label_text = node_id.replace('sat_', 'Sat_')
                ax.annotate(label_text, (x, y), 
                           fontsize=7, ha='center', va='bottom', color='black',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                   edgecolor='black', alpha=0.9, linewidth=0.5),
                           zorder=15, fontweight='bold')
    
    # Plot ground station
    if 'ground' in node_latlon:
        gs_lat, gs_lon = node_latlon['ground']
        
        if use_cartopy:
            ax.scatter(gs_lon, gs_lat, c='yellow', s=500, marker='^', 
                      edgecolors='black', linewidths=2, alpha=1.0, zorder=12,
                      transform=ccrs.PlateCarree(), label='Ground Station')
            ax.text(gs_lon, gs_lat + 3, 'Ground Sta.', fontsize=9, ha='center', 
                   fontweight='bold', color='black',
                   bbox=dict(boxstyle='round,pad=0.4', facecolor='yellow', 
                           edgecolor='black', alpha=0.9, linewidth=1.5),
                   transform=ccrs.PlateCarree(), zorder=16)
        else:
            x_gs = gs_lon * np.cos(np.radians(gs_lat))
            y_gs = gs_lat
            ax.scatter(x_gs, y_gs, c='yellow', s=500, marker='^', 
                      edgecolors='black', linewidths=2, alpha=1.0, zorder=12,
                      label='Ground Station')
            ax.annotate('Ground Sta.', (x_gs, y_gs), 
                       fontsize=9, ha='center', va='bottom', fontweight='bold', color='black',
                       bbox=dict(boxstyle='round,pad=0.4', facecolor='yellow', 
                               edgecolor='black', alpha=0.9, linewidth=1.5),
                       zorder=16)
    
    # Plot routing path if provided - make it very prominent (thick red line)
    if packet_path and len(packet_path) > 1:
        path_lons = []
        path_lats = []
        
        for node_id in packet_path:
            if node_id in node_latlon:
                lat, lon = node_latlon[node_id]
                path_lons.append(lon)
                path_lats.append(lat)
        
        # Plot routing path as thick red line (like reference)
        if use_cartopy:
            ax.plot(path_lons, path_lats, color='red', linewidth=5, alpha=0.95, 
                   linestyle='-', label='Routing Path', zorder=14,
                   transform=ccrs.PlateCarree())
        else:
            path_x = [lon * np.cos(np.radians(lat)) for lat, lon in zip(path_lats, path_lons)]
            path_y = path_lats
            ax.plot(path_x, path_y, color='red', linewidth=5, alpha=0.95, 
                   linestyle='-', label='Routing Path', zorder=14)
        
        # Highlight path nodes with larger markers
        for i, (lat, lon) in enumerate(zip(path_lats, path_lons)):
            node_id = packet_path[i]
            plane = get_plane_from_id(node_id)
            plane_color = plane_colors[plane % len(plane_colors)] if plane >= 0 else 'yellow'
            
            if use_cartopy:
                if node_id == packet_path[0]:
                    ax.scatter(lon, lat, c='blue', s=400, marker='s', 
                              edgecolors='white', linewidths=2, alpha=1.0, zorder=16,
                              transform=ccrs.PlateCarree())
                elif node_id == packet_path[-1]:
                    ax.scatter(lon, lat, c='red', s=500, marker='*', 
                              edgecolors='white', linewidths=2, alpha=1.0, zorder=16,
                              transform=ccrs.PlateCarree())
                else:
                    ax.scatter(lon, lat, c=plane_color, s=250, marker='o', 
                              edgecolors='white', linewidths=2, alpha=1.0, zorder=15,
                              transform=ccrs.PlateCarree())
            else:
                x = lon * np.cos(np.radians(lat))
                y = lat
                if node_id == packet_path[0]:
                    ax.scatter(x, y, c='blue', s=400, marker='s', 
                              edgecolors='white', linewidths=2, alpha=1.0, zorder=16)
                elif node_id == packet_path[-1]:
                    ax.scatter(x, y, c='red', s=500, marker='*', 
                              edgecolors='white', linewidths=2, alpha=1.0, zorder=16)
                else:
                    ax.scatter(x, y, c=plane_color, s=250, marker='o', 
                              edgecolors='white', linewidths=2, alpha=1.0, zorder=15)
    
    # Earth visualization is handled by Cartopy above if available
    # If not using Cartopy, continent shapes are drawn in the fallback section
    
    # Labels and formatting
    if not use_cartopy:
        ax.set_xlabel('Longitude × cos(Latitude) (Sinusoidal Projection)', fontsize=12)
        ax.set_ylabel('Latitude (degrees)', fontsize=12)
    
    ax.set_title(f'Satellite Constellation Routing: {num_planes}×{sats_per_plane} = {total_sats} satellites{title_suffix}',
                 fontsize=14, fontweight='bold', pad=15)
    
    # Add legend
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='upper left', fontsize=9, 
             ncol=2, framealpha=0.9, fancybox=True, shadow=True)
    
    plt.tight_layout()
    return fig


def plot_ground_tracks(orbit_prop, duration_minutes=90, num_points=200, packet_path=None):
    """
    Plot ground tracks of satellites on a world map, similar to ISS orbit visualization.
    
    Args:
        orbit_prop: OrbitPropagator instance
        duration_minutes: Duration to plot tracks (minutes)
        num_points: Number of points per track
        packet_path: Optional routing path to highlight
    """
    fig = plt.figure(figsize=(16, 10))
    ax = fig.add_subplot(111)
    
    # Create world map using Basemap (if available) or simple projection
    if HAS_BASEMAP:
        try:
            # Use Basemap for better map projection
            m = Basemap(projection='cyl', llcrnrlat=-90, urcrnrlat=90,
                        llcrnrlon=-180, urcrnrlon=180, resolution='c', ax=ax)
            m.drawcoastlines(linewidth=0.5, color='gray')
            m.drawcountries(linewidth=0.3, color='gray')
            m.fillcontinents(color='lightgray', lake_color='white', alpha=0.5)
            m.drawmeridians(np.arange(-180, 181, 30), labels=[0,0,0,1], linewidth=0.3, color='lightgray')
            m.drawparallels(np.arange(-90, 91, 30), labels=[1,0,0,0], linewidth=0.3, color='lightgray')
            use_basemap = True
        except:
            use_basemap = False
    else:
        use_basemap = False
    
    if not use_basemap:
        # Fallback: simple plot without map projection
        ax.set_xlim(-180, 180)
        ax.set_ylim(-90, 90)
        ax.set_xlabel('Longitude (degrees)', fontsize=12)
        ax.set_ylabel('Latitude (degrees)', fontsize=12)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.axhline(0, color='black', linewidth=0.5)  # Equator
        ax.axvline(0, color='black', linewidth=0.5)  # Prime meridian
        # Add simple continent outlines (approximate)
        # This is a very simplified representation
        ax.text(0, 0, 'Equator', ha='center', va='bottom', fontsize=8, color='gray')
        ax.text(0, 0, 'Prime Meridian', ha='left', va='center', fontsize=8, color='gray', rotation=90)
    
    # Color scheme for different planes
    plane_colors = ['red', 'orange', 'yellow', 'lime', 'cyan', 'magenta', 'pink', 'purple']
    
    # Generate ground tracks for each satellite
    duration_seconds = duration_minutes * 60
    time_points = np.linspace(0, duration_seconds, num_points)
    
    # Track which planes we've seen
    planes_plotted = set()
    
    # Get all satellites grouped by plane
    node_ids = orbit_prop.get_node_ids()
    satellites_by_plane = {}
    for node_id in node_ids:
        if node_id.startswith('sat_'):
            parts = node_id.split('_')
            if len(parts) >= 2:
                try:
                    plane = int(parts[1])
                    if plane not in satellites_by_plane:
                        satellites_by_plane[plane] = []
                    satellites_by_plane[plane].append(node_id)
                except ValueError:
                    pass
    
    # Plot ground tracks for each plane (sample one satellite per plane for clarity)
    for plane in sorted(satellites_by_plane.keys()):
        # Plot track for first satellite in each plane
        sat_id = satellites_by_plane[plane][0]
        plane_color = plane_colors[plane % len(plane_colors)]
        
        lats = []
        lons = []
        
        for t in time_points:
            positions = orbit_prop.get_positions(t)
            if sat_id in positions:
                pos = positions[sat_id]
                lat, lon = ecef_to_latlon(pos)
                lats.append(lat)
                lons.append(lon)
        
        if lats and lons:
            # Handle longitude wrapping
            lons = np.array(lons)
            lats = np.array(lats)
            
            # Unwrap longitude to avoid jumps
            lons_unwrapped = np.unwrap(np.radians(lons))
            lons_unwrapped = np.degrees(lons_unwrapped)
            
            if use_basemap:
                x, y = m(lons_unwrapped, lats)
                m.plot(x, y, color=plane_color, linewidth=2, alpha=0.7, 
                      label=f'Plane {plane} Orbit' if plane not in planes_plotted else '')
            else:
                ax.plot(lons_unwrapped, lats, color=plane_color, linewidth=2, alpha=0.7,
                       label=f'Plane {plane} Orbit' if plane not in planes_plotted else '')
            
            planes_plotted.add(plane)
    
    # Plot ground station location
    ground_pos = orbit_prop.get_positions(0)['ground']
    gs_lat, gs_lon = ecef_to_latlon(ground_pos)
    
    if use_basemap:
        gs_x, gs_y = m(gs_lon, gs_lat)
        m.plot(gs_x, gs_y, 'g^', markersize=15, label='Ground Station', 
               markeredgecolor='black', markeredgewidth=1)
    else:
        ax.plot(gs_lon, gs_lat, 'g^', markersize=15, label='Ground Station',
               markeredgecolor='black', markeredgewidth=1)
    
    # Plot routing path if provided
    if packet_path:
        path_lats = []
        path_lons = []
        for node_id in packet_path:
            if node_id in orbit_prop.get_positions(0):
                pos = orbit_prop.get_positions(0)[node_id]
                lat, lon = ecef_to_latlon(pos)
                path_lats.append(lat)
                path_lons.append(lon)
        
        if path_lats and path_lons:
            path_lons = np.array(path_lons)
            path_lats = np.array(path_lats)
            
            if use_basemap:
                path_x, path_y = m(path_lons, path_lats)
                m.plot(path_x, path_y, 'r-', linewidth=3, alpha=0.9, 
                      marker='o', markersize=8, label='Routing Path')
            else:
                ax.plot(path_lons, path_lats, 'r-', linewidth=3, alpha=0.9,
                       marker='o', markersize=8, label='Routing Path')
    
    ax.set_title(f'Satellite Ground Tracks ({duration_minutes} minutes)', 
                fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=9)
    
    plt.tight_layout()
    return fig


def compute_routing_path(router, topology, src, dst):
    """Compute routing path from source to destination."""
    # Create a dummy packet
    packet = Packet(packet_id=0, src=src, dst=dst, created_at=0, ttl=120)
    packet.current_node = src
    
    path = [src]
    visited = set([src])
    max_hops = 50  # Prevent infinite loops
    
    for _ in range(max_hops):
        if packet.current_node == dst:
            break
        
        next_hop = router.get_next_hop(packet, topology, 0, [])
        
        if next_hop is None:
            break
        
        if next_hop in visited:
            # Loop detected
            break
        
        visited.add(next_hop)
        path.append(next_hop)
        packet.current_node = next_hop
    
    if packet.current_node == dst:
        return path
    else:
        return None


def plot_constellation_3d_globe(positions, topology, orbit_prop, packet_path=None, title_suffix=""):
    """
    Plot 3D globe visualization showing Earth with satellites orbiting around it.
    Creates multiple views to clearly show orbital plane separation.
    
    Args:
        positions: Dict mapping node_id to (x, y, z) position
        topology: NetworkX graph
        orbit_prop: OrbitPropagator instance
        packet_path: Optional routing path to highlight
        title_suffix: Additional text for title
    """
    fig = plt.figure(figsize=(20, 16))
    
    # Create a single large plot with better viewing angle
    ax = fig.add_subplot(111, projection='3d')
    
    R_earth = 6378.137
    
    # Create Earth sphere with better resolution
    u = np.linspace(0, 2 * np.pi, 50)
    v = np.linspace(0, np.pi, 50)
    x_earth = R_earth * np.outer(np.cos(u), np.sin(v))
    y_earth = R_earth * np.outer(np.sin(u), np.sin(v))
    z_earth = R_earth * np.outer(np.ones(np.size(u)), np.cos(v))
    
    # Add equator line
    theta_eq = np.linspace(0, 2 * np.pi, 100)
    x_eq = R_earth * np.cos(theta_eq)
    y_eq = R_earth * np.sin(theta_eq)
    z_eq = np.zeros_like(theta_eq)
    
    # Plot Earth with texture-like appearance
    ax.plot_surface(x_earth, y_earth, z_earth, alpha=0.25, color='#4A90E2', 
                   edgecolor='#2E5C8A', linewidth=0.2, shade=True)
    
    # Add equator line
    ax.plot(x_eq, y_eq, z_eq, 'b--', alpha=0.5, linewidth=2, label='Equator')
    
    # Extract positions
    node_positions = {}
    for node_id, pos in positions.items():
        node_positions[node_id] = pos
    
    # Plot orbital planes as circles with better visibility
    if orbit_prop is not None:
        altitude_km = orbit_prop.constellation['altitude_km']
        num_planes = orbit_prop.constellation['number_of_planes']
        if 'raan_spacing_deg' in orbit_prop.constellation:
            raan_spacing = orbit_prop.constellation['raan_spacing_deg']
        else:
            raan_spacing = 360.0 / num_planes
        R_orbit = R_earth + altitude_km
        
        plane_colors = ['red', 'orange', 'yellow', 'lime', 'cyan', 'magenta', 'pink', 'purple']
        
        # Get plane-specific inclinations if available
        if hasattr(orbit_prop, 'plane_inclinations'):
            plane_inclinations = orbit_prop.plane_inclinations
        else:
            # Fallback: use base inclination for all planes
            base_inclination = orbit_prop.constellation['inclination_deg']
            plane_inclinations = [base_inclination] * num_planes
        
        print(f"Orbital plane configuration:")
        print(f"  Number of planes: {num_planes}")
        print(f"  RAAN spacing: {raan_spacing:.1f}° (each plane rotated {raan_spacing:.1f}° around Earth's axis)")
        print(f"  Plane inclinations:")
        for plane in range(num_planes):
            print(f"    Plane {plane}: {plane_inclinations[plane]:.1f}°")
        print(f"  Satellites per plane: {orbit_prop.constellation['sats_per_plane']}")
        
        # Pre-calculate orbital plane paths for all planes
        plane_paths = []
        ascending_nodes = []
        
        for plane in range(num_planes):
            raan = np.radians(plane * raan_spacing)
            inclination = np.radians(plane_inclinations[plane])  # Use plane-specific inclination
            plane_color = plane_colors[plane % len(plane_colors)]
            
            # Generate points along the orbital circle
            nu = np.linspace(0, 2 * np.pi, 200)
            r = R_orbit
            
            # Position in orbital plane
            x_orb = r * np.cos(nu)
            y_orb = r * np.sin(nu)
            z_orb = np.zeros_like(nu)
            
            # Transform to ECI frame (RAAN rotation)
            x1 = x_orb * np.cos(raan) - y_orb * np.sin(raan)
            y1 = x_orb * np.sin(raan) + y_orb * np.cos(raan)
            z1 = z_orb
            
            # Transform to ECI frame (inclination rotation)
            x2 = x1
            y2 = y1 * np.cos(inclination) - z1 * np.sin(inclination)
            z2 = y1 * np.sin(inclination) + z1 * np.cos(inclination)
            
            # Transform ECI to ECEF (Earth rotation at time 0)
            omega_earth = 7.292115e-5
            theta = omega_earth * 0
            x_ecef = x2 * np.cos(theta) - y2 * np.sin(theta)
            y_ecef = x2 * np.sin(theta) + y2 * np.cos(theta)
            z_ecef = z2
            
            plane_paths.append({
                'x': x_ecef,
                'y': y_ecef,
                'z': z_ecef,
                'color': plane_color,
                'plane': plane,
                'raan': plane * raan_spacing,
                'inclination': plane_inclinations[plane]
            })
            
            # Calculate ascending node
            nu_asc = 0
            x_asc_orb = r * np.cos(nu_asc)
            y_asc_orb = r * np.sin(nu_asc)
            z_asc_orb = 0
            
            x1_asc = x_asc_orb * np.cos(raan) - y_asc_orb * np.sin(raan)
            y1_asc = x_asc_orb * np.sin(raan) + y_asc_orb * np.cos(raan)
            z1_asc = z_asc_orb
            
            x2_asc = x1_asc
            y2_asc = y1_asc * np.cos(inclination) - z1_asc * np.sin(inclination)
            z2_asc = y1_asc * np.sin(inclination) + z1_asc * np.cos(inclination)
            
            x_asc_ecef = x2_asc * np.cos(theta) - y2_asc * np.sin(theta)
            y_asc_ecef = x2_asc * np.sin(theta) + y2_asc * np.cos(theta)
            z_asc_ecef = z2_asc
            
            ascending_nodes.append({
                'x': x_asc_ecef,
                'y': y_asc_ecef,
                'z': z_asc_ecef,
                'color': plane_color,
                'plane': plane
            })
        
        # Plot orbital planes as distinct circular orbits with thick lines
        for plane_data in plane_paths:
            # Plot the circular orbit path
            ax.plot(plane_data['x'], plane_data['y'], plane_data['z'], 
                   color=plane_data['color'], alpha=1.0, 
                   linewidth=6, linestyle='-', 
                   label=f'Plane {plane_data["plane"]} (RAAN={plane_data["raan"]:.0f}°, Inc={plane_data["inclination"]:.1f}°)',
                   zorder=5)
        
        # Mark ascending nodes with large, visible markers to show where each plane crosses equator
        for an in ascending_nodes:
            ax.scatter([an['x']], [an['y']], [an['z']], 
                      c=an['color'], s=500, marker='o', 
                      edgecolors='black', linewidths=4, alpha=1.0, zorder=11,
                      label=f'Plane {an["plane"]} Ascending Node' if an['plane'] < 2 else '')
        
        # Draw lines from center to ascending nodes to clearly show RAAN separation
        for an in ascending_nodes:
            ax.plot([0, an['x']*0.6], [0, an['y']*0.6], [0, an['z']*0.6],
                   color=an['color'], alpha=0.8, linewidth=3, linestyle=':',
                   label=f'RAAN Direction {an["plane"]*raan_spacing:.0f}°' if an['plane'] < 2 else '')
    
    # Helper function to get plane from node ID
    def get_plane_from_id(node_id):
        if node_id.startswith('sat_'):
            parts = node_id.split('_')
            if len(parts) >= 2:
                try:
                    return int(parts[1])
                except ValueError:
                    return 0
        return 0
    
    # Plot network links (light, for context)
    for edge in topology.edges():
        node1, node2 = edge
        if node1 in node_positions and node2 in node_positions:
            pos1 = node_positions[node1]
            pos2 = node_positions[node2]
            if node1.startswith('sat_') and node2.startswith('sat_'):
                ax.plot([pos1[0], pos2[0]], 
                       [pos1[1], pos2[1]], 
                       [pos1[2], pos2[2]], 
                       'gray', alpha=0.1, linewidth=0.5)
    
    # Plot routing path if provided
    if packet_path and len(packet_path) > 1:
        for i in range(len(packet_path) - 1):
            node1 = packet_path[i]
            node2 = packet_path[i + 1]
            if node1 in node_positions and node2 in node_positions:
                pos1 = node_positions[node1]
                pos2 = node_positions[node2]
                ax.plot([pos1[0], pos2[0]], 
                       [pos1[1], pos2[1]], 
                       [pos1[2], pos2[2]], 
                       'darkred', linewidth=6, alpha=0.9, 
                       label='Routing Path' if i == 0 else '')
    
    # Plot satellites with plane-based coloring - make them very visible
    plane_colors = ['red', 'orange', 'yellow', 'lime', 'cyan', 'magenta', 'pink', 'purple']
    for node_id, pos in node_positions.items():
        if node_id.startswith('sat_'):
            plane = get_plane_from_id(node_id)
            color = plane_colors[plane % len(plane_colors)]
            ax.scatter(pos[0], pos[1], pos[2], c=color, s=300, alpha=1.0, 
                      edgecolors='black', linewidths=2.5, zorder=10)
    
    # Plot ground station
    if 'ground' in node_positions:
        gs_pos = node_positions['ground']
        ax.scatter(gs_pos[0], gs_pos[1], gs_pos[2], c='green', s=800, 
                  marker='^', label='Ground Station', 
                  edgecolors='black', linewidths=3, alpha=1.0, zorder=11)
    
    # Highlight source and destination
    if packet_path:
        if packet_path[0] in node_positions:
            src_pos = node_positions[packet_path[0]]
            ax.scatter(src_pos[0], src_pos[1], src_pos[2], c='blue', s=1000, 
                      marker='s', label='Source', edgecolors='black', 
                      linewidths=3, alpha=1.0, zorder=12)
        if packet_path[-1] in node_positions:
            dst_pos = node_positions[packet_path[-1]]
            ax.scatter(dst_pos[0], dst_pos[1], dst_pos[2], c='darkred', s=1000, 
                      marker='*', label='Destination', edgecolors='black', 
                      linewidths=3, alpha=1.0, zorder=12)
    
    # Get constellation info for title
    num_planes = orbit_prop.constellation['number_of_planes'] if orbit_prop else 0
    sats_per_plane = orbit_prop.constellation['sats_per_plane'] if orbit_prop else 0
    total_sats = num_planes * sats_per_plane
    
    ax.set_xlabel('X (km)', fontsize=12)
    ax.set_ylabel('Y (km)', fontsize=12)
    ax.set_zlabel('Z (km)', fontsize=12)
    ax.set_title(f'3D Globe: {num_planes}×{sats_per_plane} = {total_sats} satellites{title_suffix}\n'
                 f'{num_planes} Distinct Circular Orbital Planes (separated by {360.0/num_planes:.0f}° RAAN)', 
                 fontsize=14, fontweight='bold', pad=20)
    
    # Set equal aspect ratio
    max_range = 8000
    ax.set_xlim([-max_range, max_range])
    ax.set_ylim([-max_range, max_range])
    ax.set_zlim([-max_range, max_range])
    
    # Set viewing angle optimized to show all 4 distinct orbits
    # Higher elevation and specific azimuth to see the circular orbits clearly separated
    ax.view_init(elev=25, azim=45)
    
    # Add legend
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='upper left', fontsize=10, ncol=1, 
             framealpha=0.9, fancybox=True, shadow=True)
    
    plt.tight_layout()
    return fig


def plot_constellation_2d(positions, topology, orbit_prop, packet_path=None, title_suffix=""):
    """
    Plot 2D constellation map showing satellites, ground station, and routing path.
    
    Args:
        positions: Dict mapping node_id to (x, y, z) position
        topology: NetworkX graph
        orbit_prop: OrbitPropagator instance
        packet_path: Optional routing path to highlight
        title_suffix: Additional text for title
    """
    fig, ax = plt.subplots(figsize=(12, 12))
    
    R_earth = 6378.137
    
    # Plot Earth circle
    circle = plt.Circle((0, 0), R_earth, fill=True, facecolor='lightblue', 
                       alpha=0.3, edgecolor='blue', linewidth=2)
    ax.add_patch(circle)
    
    # Extract positions
    node_positions = {}
    for node_id, pos in positions.items():
        node_positions[node_id] = pos
    
    # Plot orbital plane circles (projected to XY plane)
    if orbit_prop is not None:
        altitude_km = orbit_prop.constellation['altitude_km']
        num_planes = orbit_prop.constellation['number_of_planes']
        if 'raan_spacing_deg' in orbit_prop.constellation:
            raan_spacing = orbit_prop.constellation['raan_spacing_deg']
        else:
            raan_spacing = 360.0 / num_planes
        R_orbit = R_earth + altitude_km
        
        plane_colors = ['red', 'orange', 'yellow', 'lime', 'cyan', 'magenta', 'pink', 'purple']
        
        for plane in range(num_planes):
            raan = np.radians(plane * raan_spacing)
            nu = np.linspace(0, 2 * np.pi, 100)
            r = R_orbit
            
            x_orb = r * np.cos(nu)
            y_orb = r * np.sin(nu)
            
            x_rot = x_orb * np.cos(raan) - y_orb * np.sin(raan)
            y_rot = x_orb * np.sin(raan) + y_orb * np.cos(raan)
            
            plane_color = plane_colors[plane % len(plane_colors)]
            ax.plot(x_rot, y_rot, color=plane_color, alpha=0.4, linewidth=1.5, 
                   linestyle='--', label=f'Plane {plane}')
    
    # Plot network links (light gray)
    for edge in topology.edges():
        node1, node2 = edge
        if node1 in node_positions and node2 in node_positions:
            pos1 = node_positions[node1]
            pos2 = node_positions[node2]
            ax.plot([pos1[0], pos2[0]], [pos1[1], pos2[1]], 
                   'gray', alpha=0.2, linewidth=0.5, zorder=1)
    
    # Plot routing path if provided
    if packet_path and len(packet_path) > 1:
        for i in range(len(packet_path) - 1):
            node1 = packet_path[i]
            node2 = packet_path[i + 1]
            if node1 in node_positions and node2 in node_positions:
                pos1 = node_positions[node1]
                pos2 = node_positions[node2]
                ax.plot([pos1[0], pos2[0]], [pos1[1], pos2[1]], 
                       'red', linewidth=3, alpha=0.9, zorder=3,
                       label='Routing Path' if i == 0 else '')
    
    # Plot satellites with plane-based coloring
    def get_plane_from_id(node_id):
        if node_id.startswith('sat_'):
            parts = node_id.split('_')
            if len(parts) >= 2:
                try:
                    return int(parts[1])
                except ValueError:
                    return 0
        return 0
    
    plane_colors = ['orange', 'yellow', 'lime', 'magenta', 'cyan', 'pink', 'purple', 'brown']
    for node_id, pos in node_positions.items():
        if node_id.startswith('sat_'):
            plane = get_plane_from_id(node_id)
            color = plane_colors[plane % len(plane_colors)]
            ax.scatter(pos[0], pos[1], c=color, s=100, alpha=0.8, 
                      edgecolors='black', linewidths=0.5, zorder=2)
    
    # Plot ground station
    if 'ground' in node_positions:
        gs_pos = node_positions['ground']
        ax.scatter(gs_pos[0], gs_pos[1], c='green', s=300, marker='^', 
                  label='Ground Station', edgecolors='black', linewidths=2, zorder=4)
    
    # Highlight source and destination
    if packet_path:
        if packet_path[0] in node_positions:
            src_pos = node_positions[packet_path[0]]
            ax.scatter(src_pos[0], src_pos[1], c='blue', s=400, marker='s', 
                      label='Source', edgecolors='black', linewidths=2, zorder=5)
        if packet_path[-1] in node_positions:
            dst_pos = node_positions[packet_path[-1]]
            ax.scatter(dst_pos[0], dst_pos[1], c='red', s=400, marker='*', 
                      label='Destination', edgecolors='black', linewidths=2, zorder=5)
    
    # Get constellation info for title
    num_planes = orbit_prop.constellation['number_of_planes'] if orbit_prop else 0
    sats_per_plane = orbit_prop.constellation['sats_per_plane'] if orbit_prop else 0
    total_sats = num_planes * sats_per_plane
    
    ax.set_xlabel('X (km)', fontsize=12)
    ax.set_ylabel('Y (km)', fontsize=12)
    ax.set_title(f'2D Constellation Map: {num_planes}×{sats_per_plane} = {total_sats} satellites{title_suffix}', 
                fontsize=14, fontweight='bold')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right', fontsize=9, ncol=2)
    
    # Set reasonable limits
    max_range = 8000
    ax.set_xlim([-max_range, max_range])
    ax.set_ylim([-max_range, max_range])
    
    plt.tight_layout()
    return fig


def run_scaling_analysis(constellation_sizes, router_type='baseline'):
    """
    Run simulations for different constellation sizes and collect results.
    
    Args:
        constellation_sizes: List of tuples (num_planes, sats_per_plane)
        router_type: 'baseline' or 'adaptive'
    
    Returns:
        results: Dict mapping size to metrics
    """
    results = {}
    original_config = 'data/constellation.yaml'
    temp_config = 'data/constellation_temp.yaml'
    
    scenario_config = get_stable_config()
    
    for num_planes, sats_per_plane in constellation_sizes:
        size_key = f"{num_planes}x{sats_per_plane}"
        print(f"\n{'='*60}")
        print(f"Running simulation for {size_key} constellation ({num_planes * sats_per_plane} satellites)")
        print(f"{'='*60}")
        
        # Read original config
        with open(original_config, 'r') as f:
            config = yaml.safe_load(f)
        
        # Modify constellation size
        config['constellation']['number_of_planes'] = num_planes
        config['constellation']['sats_per_plane'] = sats_per_plane
        
        # Write temporary config
        with open(temp_config, 'w') as f:
            yaml.dump(config, f)
        
        try:
            # Create router
            if router_type == 'baseline':
                router = BaselineRouter()
            else:
                router = AdaptiveRouter()
            
            # Create and run simulator
            simulator = Simulator(
                constellation_config=temp_config,
                scenario_config=scenario_config,
                router=router
            )
            
            metrics = simulator.run()
            
            results[size_key] = {
                'num_planes': num_planes,
                'sats_per_plane': sats_per_plane,
                'total_sats': num_planes * sats_per_plane,
                'metrics': metrics
            }
            
            print(f"[OK] Completed {size_key}: Delivery rate = {metrics['delivery_rate']:.2%}")
            
        except Exception as e:
            print(f"[ERROR] Error running {size_key}: {e}")
            import traceback
            traceback.print_exc()
    
    # Clean up temp config
    if os.path.exists(temp_config):
        os.remove(temp_config)
    
    return results


def plot_scaling_results(results, router_type='baseline'):
    """
    Plot scaling analysis results comparing different constellation sizes.
    
    Args:
        results: Dict from run_scaling_analysis
        router_type: Router type for title
    """
    if not results:
        print("No results to plot")
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Extract data
    sizes = sorted(results.keys(), key=lambda x: results[x]['total_sats'])
    total_sats = [results[s]['total_sats'] for s in sizes]
    
    # 1. Delivery Rate
    ax = axes[0, 0]
    delivery_rates = [results[s]['metrics']['delivery_rate'] for s in sizes]
    ax.plot(total_sats, delivery_rates, 'o-', linewidth=2, markersize=10, color='blue')
    ax.set_xlabel('Total Satellites', fontsize=11)
    ax.set_ylabel('Delivery Rate', fontsize=11)
    ax.set_title(f'Delivery Rate vs Constellation Size ({router_type.capitalize()})', 
                fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_ylim([0, 1.1])
    for i, (s, rate) in enumerate(zip(total_sats, delivery_rates)):
        ax.text(s, rate + 0.02, f'{rate:.2%}', ha='center', fontsize=9)
    
    # 2. Latency (Mean)
    ax = axes[0, 1]
    latency_mean = [results[s]['metrics']['latency_mean'] for s in sizes]
    latency_median = [results[s]['metrics']['latency_median'] for s in sizes]
    latency_p95 = [results[s]['metrics']['latency_p95'] for s in sizes]
    ax.plot(total_sats, latency_mean, 'o-', label='Mean', linewidth=2, markersize=10)
    ax.plot(total_sats, latency_median, 's-', label='Median', linewidth=2, markersize=10)
    ax.plot(total_sats, latency_p95, '^-', label='P95', linewidth=2, markersize=10)
    ax.set_xlabel('Total Satellites', fontsize=11)
    ax.set_ylabel('Latency (seconds)', fontsize=11)
    ax.set_title(f'Latency vs Constellation Size ({router_type.capitalize()})', 
                fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 3. Packet Statistics
    ax = axes[1, 0]
    sent = [results[s]['metrics']['total_sent'] for s in sizes]
    delivered = [results[s]['metrics']['total_delivered'] for s in sizes]
    dropped = [results[s]['metrics']['total_dropped'] for s in sizes]
    width = 0.25
    x = np.arange(len(sizes))
    ax.bar(x - width, sent, width, label='Sent', alpha=0.8)
    ax.bar(x, delivered, width, label='Delivered', alpha=0.8)
    ax.bar(x + width, dropped, width, label='Dropped', alpha=0.8)
    ax.set_xlabel('Constellation Size', fontsize=11)
    ax.set_ylabel('Packet Count', fontsize=11)
    ax.set_title(f'Packet Statistics ({router_type.capitalize()})', 
                fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(sizes, rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # 4. Network Size vs Performance
    ax = axes[1, 1]
    ax2 = ax.twinx()
    line1 = ax.plot(total_sats, delivery_rates, 'o-', color='blue', 
                   linewidth=2, markersize=10, label='Delivery Rate')
    line2 = ax2.plot(total_sats, latency_mean, 's-', color='red', 
                    linewidth=2, markersize=10, label='Mean Latency')
    ax.set_xlabel('Total Satellites', fontsize=11)
    ax.set_ylabel('Delivery Rate', fontsize=11, color='blue')
    ax2.set_ylabel('Mean Latency (seconds)', fontsize=11, color='red')
    ax.set_title(f'Performance vs Network Size ({router_type.capitalize()})', 
                fontsize=12, fontweight='bold')
    ax.tick_params(axis='y', labelcolor='blue')
    ax2.tick_params(axis='y', labelcolor='red')
    ax.grid(True, alpha=0.3)
    
    # Combined legend
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax.legend(lines, labels, loc='upper left')
    
    plt.tight_layout()
    return fig


def main():
    """Generate 2D constellation maps and scaling analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Visualize constellation and run scaling analysis')
    parser.add_argument('--mode', choices=['single', 'scaling'], default='single',
                       help='Mode: single (one constellation) or scaling (multiple sizes)')
    parser.add_argument('--router', choices=['baseline', 'adaptive'], default='baseline',
                       help='Router type for scaling analysis')
    parser.add_argument('--sizes', nargs='+', default=['4x4', '6x6', '8x8'],
                       help='Constellation sizes for scaling (e.g., 4x4 6x6 8x8)')
    
    args = parser.parse_args()
    
    if args.mode == 'single':
        # Original single constellation visualization
        print("Loading constellation...")
        
        op = OrbitPropagator('data/constellation.yaml')
        vc = VisibilityChecker(isl_range_km=5000, elevation_threshold_deg=5)
        tb = TopologyBuilder(vc)
        router = BaselineRouter()
        
        time = 0
        positions = op.get_positions(time)
        topology = tb.build_topology(positions)
        
        node_ids = op.get_node_ids()
        src = 'ground'
        num_planes = op.constellation['number_of_planes']
        sats_per_plane = op.constellation['sats_per_plane']
        
        # Select a random satellite consistently (same as simulator logic)
        satellites = [n for n in node_ids if n.startswith('sat_')]
        if satellites:
            # Use same deterministic seed as simulator
            seed_string = f"{num_planes}x{sats_per_plane}"
            seed = int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)
            random.seed(seed)
            dst = random.choice(satellites)
            random.seed()  # Reset to system random
        else:
            dst = None
        
        print(f"Computing routing path from {src} to {dst}...")
        path = compute_routing_path(router, topology, src, dst)
        
        if path:
            print(f"Path found ({len(path)-1} hops)")
        else:
            path = [src, dst] if dst else [src]
        
        # Create 2D constellation map
        print("Generating 2D constellation map...")
        fig = plot_constellation_2d(positions, topology, op, path)
        
        output_path = 'outputs/plots/constellation_2d.png'
        os.makedirs('outputs/plots', exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"2D map saved to: {output_path}")
        plt.close(fig)
        
        # Create 3D globe visualization
        print("Generating 3D globe visualization...")
        fig3d = plot_constellation_3d_globe(positions, topology, op, path)
        
        output_path_3d = 'outputs/plots/constellation_3d_globe.png'
        fig3d.savefig(output_path_3d, dpi=150, bbox_inches='tight')
        print(f"3D globe saved to: {output_path_3d}")
        plt.close(fig3d)
        
        # Create sinusoidal 2D routing visualization
        print("Generating sinusoidal 2D routing view...")
        fig_sin = plot_sinusoidal_2d_routing(positions, topology, op, path)
        
        output_path_sin = 'outputs/plots/routing_sinusoidal_2d.png'
        fig_sin.savefig(output_path_sin, dpi=150, bbox_inches='tight')
        print(f"Sinusoidal 2D routing view saved to: {output_path_sin}")
        plt.close(fig_sin)
        
    else:  # scaling mode
        print("Running scaling analysis...")
        
        # Parse sizes
        constellation_sizes = []
        for size_str in args.sizes:
            try:
                parts = size_str.split('x')
                num_planes = int(parts[0])
                sats_per_plane = int(parts[1])
                constellation_sizes.append((num_planes, sats_per_plane))
            except:
                print(f"Warning: Invalid size format '{size_str}', skipping")
        
        if not constellation_sizes:
            constellation_sizes = [(4, 4), (6, 6), (8, 8)]
        
        # Run simulations
        results = run_scaling_analysis(constellation_sizes, args.router)
        
        if results:
            # Plot scaling results
            print("\nGenerating scaling analysis plots...")
            fig = plot_scaling_results(results, args.router)
            
            output_path = f'outputs/plots/scaling_analysis_{args.router}.png'
            os.makedirs('outputs/plots', exist_ok=True)
            fig.savefig(output_path, dpi=150, bbox_inches='tight')
            print(f"Scaling analysis saved to: {output_path}")
            
            # Generate all visualizations for each size
            print("\nGenerating visualizations for each constellation size...")
            original_config = 'data/constellation.yaml'
            temp_config = 'data/constellation_temp.yaml'
            
            for size_key in results.keys():
                num_planes = results[size_key]['num_planes']
                sats_per_plane = results[size_key]['sats_per_plane']
                
                print(f"\n  Processing {size_key} ({num_planes}×{sats_per_plane} = {num_planes * sats_per_plane} satellites)...")
                
                # Read and modify config
                with open(original_config, 'r') as f:
                    config = yaml.safe_load(f)
                config['constellation']['number_of_planes'] = num_planes
                config['constellation']['sats_per_plane'] = sats_per_plane
                with open(temp_config, 'w') as f:
                    yaml.dump(config, f)
                
                # Initialize components
                op = OrbitPropagator(temp_config)
                vc = VisibilityChecker(isl_range_km=5000, elevation_threshold_deg=5)
                tb = TopologyBuilder(vc)
                router = BaselineRouter()
                
                positions = op.get_positions(0)
                topology = tb.build_topology(positions)
                
                src = 'ground'
                # Select a random satellite consistently (same as simulator logic)
                node_ids = op.get_node_ids()
                satellites = [n for n in node_ids if n.startswith('sat_')]
                if satellites:
                    seed_string = f"{num_planes}x{sats_per_plane}"
                    seed = int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)
                    random.seed(seed)
                    dst = random.choice(satellites)
                    random.seed()  # Reset to system random
                else:
                    dst = None
                path = compute_routing_path(router, topology, src, dst) if dst else None
                if not path:
                    path = [src, dst]
                
                # Generate 2D constellation map
                print(f"    Generating 2D map...")
                fig = plot_constellation_2d(positions, topology, op, path, 
                                          f" ({size_key})")
                map_path = f'outputs/plots/constellation_2d_{size_key}.png'
                fig.savefig(map_path, dpi=150, bbox_inches='tight')
                print(f"    [OK] {map_path}")
                plt.close(fig)
                
                # Generate 3D globe for each size
                print(f"    Generating 3D globe...")
                fig3d = plot_constellation_3d_globe(positions, topology, op, path, 
                                                    f" ({size_key})")
                map_path_3d = f'outputs/plots/constellation_3d_globe_{size_key}.png'
                fig3d.savefig(map_path_3d, dpi=150, bbox_inches='tight')
                print(f"    [OK] {map_path_3d}")
                plt.close(fig3d)
                
                # Generate sinusoidal 2D routing view for each size
                print(f"    Generating sinusoidal 2D routing view...")
                fig_sin = plot_sinusoidal_2d_routing(positions, topology, op, path, 
                                                     f" ({size_key})")
                map_path_sin = f'outputs/plots/routing_sinusoidal_2d_{size_key}.png'
                fig_sin.savefig(map_path_sin, dpi=150, bbox_inches='tight')
                print(f"    [OK] {map_path_sin}")
                plt.close(fig_sin)
            
            # Clean up
            if os.path.exists(temp_config):
                os.remove(temp_config)
            
            # Save results JSON
            json_path = f'outputs/scaling_results_{args.router}.json'
            with open(json_path, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to: {json_path}")
            
            # Don't show plots in batch mode (they're already saved)
            # plt.show()  # Commented out for batch processing
        else:
            print("No results generated")


if __name__ == '__main__':
    main()
