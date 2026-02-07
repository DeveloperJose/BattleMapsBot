import asyncio
import time
import logging
import statistics

from src.core.repository import MapRepository
from src.core.aw2_renderer import AW2Renderer

# Setup logging to avoid cluttering output
logging.basicConfig(level=logging.CRITICAL)


MAP_IDS = [
    69669,  # Small map (25x25)
    179270,  # Large 6 player map (50x44)
    153643,
    111366,
    102523,
    160183,
    153592,
    168502,  # Special emphasis
]


async def prepare_data():
    """Fetch all maps once to ensure they are cached."""
    print("Pre-fetching map data...")
    repo = MapRepository()
    for map_id in MAP_IDS:
        try:
            print(f"Fetching {map_id}...")
            await repo.get_map_data(map_id)
        except Exception as e:
            print(f"Failed to fetch {map_id}: {e}")

    await repo.close()
    print("Data preparation complete.")


def benchmark():
    print("\nStarting Benchmark...")
    repo = MapRepository()  # Use cached data
    renderer = AW2Renderer()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    map_data_cache = {}

    # Load all data into memory first to isolate rendering time
    async def load_maps():
        for map_id in MAP_IDS:
            map_data_cache[map_id] = await repo.get_map_data(map_id)

    loop.run_until_complete(load_maps())
    loop.close()

    results = {}

    for map_id in MAP_IDS:
        data = map_data_cache.get(map_id)
        if not data:
            print(f"Skipping {map_id} (no data)")
            continue

        times = []
        # Warmup
        renderer.render_map(data)

        # Run 5 times
        for _ in range(5):
            start = time.perf_counter()
            renderer.render_map(data)
            end = time.perf_counter()
            times.append(end - start)

        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        results[map_id] = avg_time

        print(
            f"Map {map_id} ({data['size_w']}x{data['size_h']}): Avg: {avg_time * 1000:.2f}ms (Min: {min_time * 1000:.2f}ms, Max: {max_time * 1000:.2f}ms)"
        )

    return results


if __name__ == "__main__":
    try:
        asyncio.run(prepare_data())
        benchmark()
    except KeyboardInterrupt:
        pass
