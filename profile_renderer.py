import asyncio
import cProfile
import pstats
import logging

from src.core.repository import MapRepository
from src.core.aw2_renderer import AW2Renderer

# Setup logging to avoid cluttering output
logging.basicConfig(level=logging.CRITICAL)

# Use a large map for a more representative profile
MAP_ID = 179270


async def main():
    """Fetches map data, runs the renderer under cProfile, and prints stats."""
    print(f"Profiling renderer with Map ID: {MAP_ID}")

    # 1. Fetch map data
    repo = MapRepository()
    try:
        map_data = await repo.get_map_data(MAP_ID)
    except Exception as e:
        print(f"Failed to fetch map data for {MAP_ID}: {e}")
        return
    finally:
        await repo.close()

    if not map_data:
        print("No map data found. Exiting.")
        return

    # 2. Setup renderer and profiler
    renderer = AW2Renderer()
    profiler = cProfile.Profile()

    # 3. Run the rendering function under the profiler
    # Run once as a warmup
    renderer.render_map(map_data)

    print("\nRunning profiler...")
    profiler.enable()
    renderer.render_map(map_data)
    profiler.disable()
    print("Profiling complete.")

    # 4. Print the stats
    print("\n--- Profiling Results ---")
    stats = pstats.Stats(profiler).sort_stats("cumtime")
    stats.print_stats(30)  # Print the top 30 cumulative time offenders

    # Optional: Dump stats to a file for more detailed analysis
    profile_dump_file = "renderer.prof"
    stats.dump_stats(profile_dump_file)
    print(f"\nProfile data saved to '{profile_dump_file}'.")
    print(
        "Look for high `cumtime` in functions related to Pillow (PIL) image operations."
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProfiling interrupted.")
