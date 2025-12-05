import sys
import os
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates # Added for the new 2D plot
from datetime import date, timedelta
from concurrent.futures import ProcessPoolExecutor
from functools import partial

# Check for Cartopy (Mandatory)
try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    HAS_CARTOPY = True
except ImportError:
    HAS_CARTOPY = False
    print("CRITICAL: 'cartopy' library not found.")

# ==============================================================================
# Path Configuration & Imports
# ==============================================================================

current_file_path = os.path.abspath(__file__)
examples_dir = os.path.dirname(current_file_path)
project_root = os.path.dirname(examples_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from src.engine.solver import SolarEventSolver
except ImportError as e:
    # This might happen in worker processes if path isn't propagated, 
    # but typically fork handles it.
    pass

# ==============================================================================
# Worker Logic (Must be top-level for multiprocessing)
# ==============================================================================

def compute_latitude_band(lat, dates):
    """
    Worker function to compute LOD derivative for a single latitude across all dates.
    Uses Central Difference: (LOD(t+1) - LOD(t-1)) / 2
    """
    # Re-import inside worker to ensure clean state
    from src.engine.solver import SolarEventSolver
    solver = SolarEventSolver()
    
    lon = 0.0
    row_data = np.zeros(len(dates))
    
    for j, current_date in enumerate(dates):
        # Central Difference: f'(x) approx (f(x+h) - f(x-h)) / 2h
        # h = 1 day
        
        date_prev = current_date - timedelta(days=1)
        date_next = current_date + timedelta(days=1)
        
        # We need robust error handling for polar endless days/nights
        res_prev = solver.solve_for_date(date_prev, lat, lon)
        res_next = solver.solve_for_date(date_next, lat, lon)
        
        lod_prev = res_prev.duration_hours
        lod_next = res_next.duration_hours
        
        # Handle the singularity at polar circle crossings where LOD jumps 0->24 or 24->0
        # If the jump is massive (> 12 hours), it's not a rate of change, it's a state switch.
        diff_hours = lod_next - lod_prev
        
        if abs(diff_hours) > 12.0:
            # Mask this point or cap it. We chose to zero it to avoid rendering artifacts.
            delta_min = 0.0
        else:
            # Change over 2 days, so divide by 2 to get rate per day
            delta_min = (diff_hours * 60.0) / 2.0
            
        row_data[j] = delta_min
        
    return row_data

# ==============================================================================
# Analysis & Plotting Routines
# ==============================================================================

def plot_peak_velocities(dates, lats, grid):
    """
    Identifies and plots the dates of maximum positive/negative change.
    This creates a standard 2D plot (Lat vs Date).
    """
    print("\n--- Generating Peak Velocity Analysis ---")
    
    # grid shape: (lats, dates)
    # Find indices of global maxima (Fastest Gain) and minima (Fastest Loss) along the time axis
    idx_gain = np.argmax(grid, axis=1)
    idx_loss = np.argmin(grid, axis=1)
    
    # Extract values to filter out dead zones (poles where change might be 0)
    val_gain = np.max(grid, axis=1)
    val_loss = np.min(grid, axis=1)
    
    # Filter masks (ignore regions with negligible change, e.g., < 0.1 min/day)
    # This removes the deep polar night/day regions where LOD is constant
    mask_gain = val_gain > 0.1
    mask_loss = val_loss < -0.1
    
    # Convert list of dates to numpy array for indexing
    dates_arr = np.array(dates)
    
    # Apply masks
    dates_gain = dates_arr[idx_gain][mask_gain]
    lats_gain = lats[mask_gain]
    
    dates_loss = dates_arr[idx_loss][mask_loss]
    lats_loss = lats[mask_loss]
    
    # Create New Figure
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
    
    # Plot Gain (Spring)
    ax.plot(dates_gain, lats_gain, color='tab:blue', linewidth=2.5, label='Fastest Gain (Spring)')
    
    # Plot Loss (Autumn)
    ax.plot(dates_loss, lats_loss, color='tab:red', linewidth=2.5, label='Fastest Loss (Autumn)')
    
    # Formatting
    ax.set_title("Timing of Peak Seasonal Change", fontsize=16, fontweight='bold')
    ax.set_xlabel("Date of Max Velocity", fontsize=12)
    ax.set_ylabel("Latitude", fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(fontsize=12)
    
    # Limits
    ax.set_ylim(-90, 90)
    ax.set_yticks(np.arange(-90, 91, 15))
    
    # X-Axis Date Formatting
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    
    # Add annotations for context
    # Note: These are rough placements, they will adjust dynamically
    if len(dates_gain) > 0:
        mid_idx = len(dates_gain) // 2
        ax.text(dates_gain[mid_idx], lats_gain[mid_idx] - 5, "Spring Equinox\nWave", 
                color='tab:blue', ha='center', fontsize=9, fontweight='bold')
        
    if len(dates_loss) > 0:
        mid_idx = len(dates_loss) // 2
        ax.text(dates_loss[mid_idx], lats_loss[mid_idx] + 5, "Autumn Equinox\nWave", 
                color='tab:red', ha='center', fontsize=9, fontweight='bold')

    plt.tight_layout()

# ==============================================================================
# Main Orchestration
# ==============================================================================

def calculate_seasonal_velocity_map_parallel(year, lat_steps=180, day_step=1):
    """
    Computes LOD rate of change grid using Parallel Processing.
    """
    # Full globe coverage
    lats = np.linspace(-90, 90, lat_steps)
    
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    total_days = (end_date - start_date).days
    
    # Generate date list
    sample_dates = [start_date + timedelta(days=i) for i in range(0, total_days, day_step)]
    
    print(f"--- Starting Simulation for {year} ---")
    print(f"Grid: {len(lats)} Latitudes x {len(sample_dates)} Days")
    print(f"CPUs: {os.cpu_count()} cores available")
    
    t0 = time.time()
    
    # Prepare arguments for map
    # We fix 'dates' and vary 'lat'
    func = partial(compute_latitude_band, dates=sample_dates)
    
    # Execute in parallel
    results = []
    with ProcessPoolExecutor() as executor:
        # Map returns results in order
        results = list(executor.map(func, lats))
            
    # Stack results into 2D array
    velocity_grid = np.vstack(results)
    
    elapsed = time.time() - t0
    print(f"--- Calculation Complete in {elapsed:.2f}s ---")

    return sample_dates, lats, velocity_grid

def main():
    if not HAS_CARTOPY:
        print("Error: Cartopy is required.")
        return

    # 1. Configuration
    YEAR = 2025
    # High Resolution settings
    LAT_STEPS = 360  # 0.5 degree resolution
    DAY_STEP = 1     # Daily resolution
    
    dates, lats, grid = calculate_seasonal_velocity_map_parallel(YEAR, LAT_STEPS, DAY_STEP)
    
    # 2. Setup Map Projection
    # PlateCarree maps (Lon, Lat) -> (X, Y) linearly.
    # We use this to map (Time, Lat) -> (X, Y).
    fig = plt.figure(figsize=(12, 7), dpi=150) 
    ax = plt.axes(projection=ccrs.PlateCarree())
    
    # Force extent to ensure we see the full +/- 180 range (critical for tick visibility)
    ax.set_extent([-180, 180, -90, 90], crs=ccrs.PlateCarree())
    
    # 3. Create the "Time-Longitude" Mesh
    # Map [Jan 1 .. Dec 31] -> [-180 .. 180]
    lon_simulated = np.linspace(-180, 180, len(dates))
    
    # 4. Plot Heatmap
    # 'RdBu': Red = Days shortening, Blue = Days lengthening
    mesh = ax.pcolormesh(lon_simulated, lats, grid, 
                         transform=ccrs.PlateCarree(),
                         cmap='RdBu', shading='gouraud', 
                         vmin=-6, vmax=6, alpha=0.9)

    # 4b. Add Contour Lines (Quantifies the gradient)
    # We plot lines at -6, -4, -2, +2, +4, +6 minutes per day
    cs = ax.contour(lon_simulated, lats, grid, 
                    transform=ccrs.PlateCarree(),
                    levels=[-6, -4, -2, 2, 4, 6], 
                    colors='black', alpha=0.3, linewidths=0.5)
    ax.clabel(cs, inline=True, fmt='%1.0f min', fontsize=8)

    # 5. Overlay Geographic Features
    ax.add_feature(cfeature.LAND, facecolor='none', edgecolor='black', alpha=0.1)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8, edgecolor='black', alpha=0.4)
    ax.add_feature(cfeature.BORDERS, linestyle=':', alpha=0.3)
    
    # 6. Overlay: Major Cities for Context
    # Since X is longitude, plotting the city at its ACTUAL longitude places it
    # at the time of year corresponding to that longitude.
    # West (Americas) = Jan-Jun
    # East (Asia) = Jul-Dec
    cities = [
        ('New York', 40.7, -74.0),
        ('London', 51.5, 0.0),
        ('Tokyo', 35.7, 139.7),
        ('Sydney', -33.9, 151.2),
        ('Buenos Aires', -34.6, -58.4),
        ('Singapore', 1.3, 103.8),
        ('Cape Town', -33.9, 18.4)
    ]
    
    for name, lat, lon in cities:
        ax.plot(lon, lat, 'ko', markersize=4, transform=ccrs.PlateCarree(), alpha=0.7)
        ax.text(lon + 2, lat + 1, name, transform=ccrs.PlateCarree(), 
                fontsize=8, fontweight='bold', alpha=0.8,
                bbox=dict(facecolor='white', alpha=0.6, pad=1, edgecolor='none'))

    # 7. Overlay: Solar Declination Track (Approximate)
    # The sun's declination moves from -23.4 to +23.4. 
    # This line shows where the sun is overhead.
    # We can approximate declination ~ -23.44 * cos(radians)
    # We map the 360 degrees of longitude to the 360 degrees of the year orbit
    # Note: Phase shift needed. Jan 1 is near perihelion/solstice.
    # Winter Solstice ~Dec 21. Jan 1 is ~10 days after.
    # Longitude -180 is Jan 1.
    rads = np.radians(lon_simulated + 180 + 10) # +10 deg phase shift approx
    declination = -23.44 * np.cos(rads)
    
    ax.plot(lon_simulated, declination, color='gold', linestyle='--', linewidth=1.5, 
            transform=ccrs.PlateCarree(), label='Sub-Solar Point (Zenith)')
    
    # 8. Custom Axis Formatting (Time instead of Longitude)
    # We hijack the gridlines to show months instead of degrees
    # Create ticks every 30 degrees (approx 1 month)
    tick_locs = np.arange(-180, 181, 30) 
    
    gl = ax.gridlines(draw_labels=True, linewidth=1, color='gray', alpha=0.3, linestyle='--')
    
    # Configure Placement
    gl.top_labels = True
    gl.bottom_labels = True
    gl.left_labels = True
    gl.right_labels = False
    
    # Configure Locators
    gl.xlocator = mticker.FixedLocator(tick_locs)
    gl.ylocator = mticker.FixedLocator(np.arange(-90, 91, 15))
    
    # Use FuncFormatter for robustness
    # This ensures that even if Cartopy passes a value instead of an index, we map it correctly
    def format_month(x, pos):
        # Map Longitude -180..180 to Month Index 0..12
        # -180 = Jan, -150 = Feb, ...
        # Formula: Index = (x + 180) / 30
        idx = int(round((x + 180) / 30))
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', '']
        if 0 <= idx < len(months):
            return months[idx]
        return ""
        
    gl.xformatter = mticker.FuncFormatter(format_month)
    
    # Styling
    gl.xlabel_style = {'size': 11, 'color': 'black', 'weight': 'bold'}
    gl.ylabel_style = {'size': 10}
    
    # Titles and Legends
    plt.title(f"Earth's Seasonal Velocity ({YEAR})\n"
              f"Visualizing the Rate of Daylight Change [min/day]", 
              fontsize=18, fontweight='bold', pad=15)
    
    # Annotations
    ax.text(-175, 85, "Days Lengthening (+)", color='blue', fontweight='bold', 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
    ax.text(-175, 80, "Days Shortening (-)", color='firebrick', fontweight='bold',
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))

    # Colorbar
    cbar = plt.colorbar(mesh, ax=ax, orientation='horizontal', pad=0.08, aspect=60, shrink=0.7)
    cbar.set_label('Daily Change in Sunlight (minutes)', fontsize=12, fontweight='bold')
    cbar.ax.minorticks_on()
    
    plt.tight_layout()
    
    # 9. Generate Second Figure (Peak Dates)
    plot_peak_velocities(dates, lats, grid)

    plt.show()

if __name__ == "__main__":
    main()