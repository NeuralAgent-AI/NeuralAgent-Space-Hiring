# Data Directory

This directory contains configuration files for the satellite constellation simulation.

## Files

### `constellation.yaml`

Main configuration file for the satellite constellation and ground station.

**What to modify:**
- `number_of_planes`: Number of orbital planes (for scaling analysis: 4, 6, 8, 10)
- `sats_per_plane`: Number of satellites per plane (for scaling analysis: 4, 6, 8, 10)
- `ground_station.lat_deg` / `ground_station.lon_deg`: Ground station location

**What to keep constant (for fair comparison):**
- `altitude_km`: 550 km
- `inclination_deg`: 53° (base value)
- `ground_station` location

## Quick Configuration Guide

### For Scaling Analysis

Test your routing algorithm with progressively larger constellations:

1. **Small (16 satellites)**:
   ```yaml
   number_of_planes: 4
   sats_per_plane: 4
   ```

2. **Medium (36 satellites)**:
   ```yaml
   number_of_planes: 6
   sats_per_plane: 6
   ```

3. **Large (64 satellites)**:
   ```yaml
   number_of_planes: 8
   sats_per_plane: 8
   ```

4. **Extra Large (100 satellites)**:
   ```yaml
   number_of_planes: 10
   sats_per_plane: 10
   ```

### Running Experiments

After modifying `constellation.yaml`, run:

```bash
# Test with baseline router
python run.py --scenario stable --router baseline

# Test with your adaptive router
python run.py --scenario stable --router adaptive

# Test with disrupted scenario
python run.py --scenario disrupted --router adaptive
```

### Visualization

Generate visualizations for the current configuration:

```bash
# Single constellation view
python plots/visualize_topology.py --mode single

# All constellation sizes (automatically tests 4x4, 6x6, 8x8, 10x10)
python plots/visualize_topology.py --mode scaling --sizes 4x4 6x6 8x8 10x10
```

## Parameter Details

See comments in `constellation.yaml` for detailed explanations of each parameter.
