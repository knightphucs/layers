"""
LAYERS - Performance Benchmark Script
========================================
Run this to verify all operations meet performance targets.
No database needed — tests pure Python logic speed.

Run: python scripts/benchmark.py
"""

import time
import statistics
from datetime import datetime, timedelta
from uuid import uuid4


def benchmark(name: str, func, iterations: int = 10_000):
    """Run a function N times and report timing statistics."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        times.append((time.perf_counter() - start) * 1_000_000)  # microseconds

    avg = statistics.mean(times)
    p50 = statistics.median(times)
    p95 = sorted(times)[int(0.95 * len(times))]
    p99 = sorted(times)[int(0.99 * len(times))]
    total_ms = sum(times) / 1000

    target = "✅" if p95 < 100 else "⚠️"  # Target: p95 < 100µs

    print(f"  {target} {name}")
    print(f"     Iterations: {iterations:,}")
    print(f"     Total: {total_ms:.1f}ms")
    print(f"     Avg: {avg:.1f}µs | P50: {p50:.1f}µs | P95: {p95:.1f}µs | P99: {p99:.1f}µs")
    print()

    return {"name": name, "avg_us": avg, "p95_us": p95, "p99_us": p99}


def main():
    print("=" * 60)
    print("⚡ LAYERS — Performance Benchmark Report")
    print("=" * 60)
    print(f"   Date: {datetime.utcnow().isoformat()}")
    print(f"   Target: All operations < 100µs (p95)\n")

    results = []

    # ---- 1. Haversine Distance ----
    print("📐 Haversine Distance Calculation")
    print("-" * 40)
    from app.services.anti_cheat_service import haversine_meters

    results.append(benchmark(
        "haversine_meters(short ~100m)",
        lambda: haversine_meters(10.7725, 106.6980, 10.7734, 106.6980),
    ))
    results.append(benchmark(
        "haversine_meters(long ~800m)",
        lambda: haversine_meters(10.7725, 106.6980, 10.7798, 106.6990),
    ))

    # ---- 2. Chunk Calculation ----
    print("🗺️ Fog of War Chunk Calculation")
    print("-" * 40)
    from app.services.exploration_service import _calculate_chunk

    results.append(benchmark(
        "_calculate_chunk(HCMC)",
        lambda: _calculate_chunk(10.7725, 106.6980),
    ))
    results.append(benchmark(
        "_calculate_chunk(equator)",
        lambda: _calculate_chunk(0.001, 0.001),
    ))

    # ---- 3. isMocked Check ----
    print("🛡️ Anti-Cheat: isMocked Check")
    print("-" * 40)
    from app.services.anti_cheat_service import check_is_mocked, LocationMetadata

    clean_meta = LocationMetadata(
        latitude=10.7725, longitude=106.6980,
        is_mocked=False, provider="gps",
    )
    results.append(benchmark(
        "check_is_mocked(clean)",
        lambda: check_is_mocked(clean_meta),
    ))

    # ---- 4. Teleport Detection ----
    print("🛡️ Anti-Cheat: Teleport Detection")
    print("-" * 40)
    from app.services.anti_cheat_service import (
        check_teleport, LocationHistoryEntry
    )

    history = [LocationHistoryEntry(
        latitude=10.7725, longitude=106.6980,
        timestamp=datetime.utcnow() - timedelta(seconds=30),
    )]
    walk_meta = LocationMetadata(
        latitude=10.7730, longitude=106.6982,
        timestamp=datetime.utcnow(),
    )
    results.append(benchmark(
        "check_teleport(normal walk)",
        lambda: check_teleport(walk_meta, history),
    ))

    # ---- 5. Sensor Mismatch ----
    print("🛡️ Anti-Cheat: Sensor Mismatch")
    print("-" * 40)
    from app.services.anti_cheat_service import check_sensor_mismatch

    sensor_meta = LocationMetadata(
        latitude=10.7730, longitude=106.6982,
        accelerometer_magnitude=10.5,
        timestamp=datetime.utcnow(),
    )
    results.append(benchmark(
        "check_sensor_mismatch(walking)",
        lambda: check_sensor_mismatch(sensor_meta, history),
    ))

    # ---- 6. Full Anti-Cheat Pipeline ----
    print("🛡️ Anti-Cheat: FULL Pipeline (all checks)")
    print("-" * 40)
    import asyncio
    from app.services.anti_cheat_service import AntiCheatService, clear_user_history

    uid = uuid4()

    async def run_pipeline():
        return await AntiCheatService.analyze_location(uid, clean_meta)

    # Warm up
    asyncio.run(run_pipeline())

    pipeline_times = []
    for _ in range(1_000):
        start = time.perf_counter()
        asyncio.run(run_pipeline())
        pipeline_times.append((time.perf_counter() - start) * 1_000_000)

    clear_user_history(uid)

    avg = statistics.mean(pipeline_times)
    p95 = sorted(pipeline_times)[int(0.95 * len(pipeline_times))]
    target = "✅" if avg < 500 else "⚠️"  # Pipeline target: <500µs avg

    print(f"  {target} Full pipeline (1,000 iterations)")
    print(f"     Avg: {avg:.0f}µs | P95: {p95:.0f}µs")
    print()

    # ---- SUMMARY ----
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    passed = sum(1 for r in results if r["p95_us"] < 100)
    total = len(results)
    print(f"\n  Tests passed: {passed}/{total} (target: p95 < 100µs)")
    print(f"  Pipeline avg: {avg:.0f}µs (target: < 500µs)")

    if passed == total and avg < 500:
        print("\n  🎉 ALL BENCHMARKS PASS! Ready for production.")
    else:
        print("\n  ⚠️  Some benchmarks need attention. Check results above.")

    print()


if __name__ == "__main__":
    main()
"""
LAYERS - Performance Benchmark Script
========================================
FILE: backend/scripts/benchmark.py

Run this to verify all operations meet performance targets.
No database needed — tests pure Python logic speed.

Run: python scripts/benchmark.py
"""

import time
import statistics
from datetime import datetime, timedelta
from uuid import uuid4


def benchmark(name: str, func, iterations: int = 10_000):
    """Run a function N times and report timing statistics."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        times.append((time.perf_counter() - start) * 1_000_000)  # microseconds

    avg = statistics.mean(times)
    p50 = statistics.median(times)
    p95 = sorted(times)[int(0.95 * len(times))]
    p99 = sorted(times)[int(0.99 * len(times))]
    total_ms = sum(times) / 1000

    target = "✅" if p95 < 100 else "⚠️"  # Target: p95 < 100µs

    print(f"  {target} {name}")
    print(f"     Iterations: {iterations:,}")
    print(f"     Total: {total_ms:.1f}ms")
    print(f"     Avg: {avg:.1f}µs | P50: {p50:.1f}µs | P95: {p95:.1f}µs | P99: {p99:.1f}µs")
    print()

    return {"name": name, "avg_us": avg, "p95_us": p95, "p99_us": p99}


def main():
    print("=" * 60)
    print("⚡ LAYERS — Performance Benchmark Report")
    print("=" * 60)
    print(f"   Date: {datetime.utcnow().isoformat()}")
    print(f"   Target: All operations < 100µs (p95)\n")

    results = []

    # ---- 1. Haversine Distance ----
    print("📐 Haversine Distance Calculation")
    print("-" * 40)
    from app.services.anti_cheat_service import haversine_meters

    results.append(benchmark(
        "haversine_meters(short ~100m)",
        lambda: haversine_meters(10.7725, 106.6980, 10.7734, 106.6980),
    ))
    results.append(benchmark(
        "haversine_meters(long ~800m)",
        lambda: haversine_meters(10.7725, 106.6980, 10.7798, 106.6990),
    ))

    # ---- 2. Chunk Calculation ----
    print("🗺️ Fog of War Chunk Calculation")
    print("-" * 40)
    from app.services.exploration_service import _calculate_chunk

    results.append(benchmark(
        "_calculate_chunk(HCMC)",
        lambda: _calculate_chunk(10.7725, 106.6980),
    ))
    results.append(benchmark(
        "_calculate_chunk(equator)",
        lambda: _calculate_chunk(0.001, 0.001),
    ))

    # ---- 3. isMocked Check ----
    print("🛡️ Anti-Cheat: isMocked Check")
    print("-" * 40)
    from app.services.anti_cheat_service import check_is_mocked, LocationMetadata

    clean_meta = LocationMetadata(
        latitude=10.7725, longitude=106.6980,
        is_mocked=False, provider="gps",
    )
    results.append(benchmark(
        "check_is_mocked(clean)",
        lambda: check_is_mocked(clean_meta),
    ))

    # ---- 4. Teleport Detection ----
    print("🛡️ Anti-Cheat: Teleport Detection")
    print("-" * 40)
    from app.services.anti_cheat_service import (
        check_teleport, LocationHistoryEntry
    )

    history = [LocationHistoryEntry(
        latitude=10.7725, longitude=106.6980,
        timestamp=datetime.utcnow() - timedelta(seconds=30),
    )]
    walk_meta = LocationMetadata(
        latitude=10.7730, longitude=106.6982,
        timestamp=datetime.utcnow(),
    )
    results.append(benchmark(
        "check_teleport(normal walk)",
        lambda: check_teleport(walk_meta, history),
    ))

    # ---- 5. Sensor Mismatch ----
    print("🛡️ Anti-Cheat: Sensor Mismatch")
    print("-" * 40)
    from app.services.anti_cheat_service import check_sensor_mismatch

    sensor_meta = LocationMetadata(
        latitude=10.7730, longitude=106.6982,
        accelerometer_magnitude=10.5,
        timestamp=datetime.utcnow(),
    )
    results.append(benchmark(
        "check_sensor_mismatch(walking)",
        lambda: check_sensor_mismatch(sensor_meta, history),
    ))

    # ---- 6. Full Anti-Cheat Pipeline ----
    print("🛡️ Anti-Cheat: FULL Pipeline (all checks)")
    print("-" * 40)
    import asyncio
    from app.services.anti_cheat_service import AntiCheatService, clear_user_history

    uid = uuid4()

    async def run_pipeline():
        return await AntiCheatService.analyze_location(uid, clean_meta)

    # Warm up
    asyncio.run(run_pipeline())

    pipeline_times = []
    for _ in range(1_000):
        start = time.perf_counter()
        asyncio.run(run_pipeline())
        pipeline_times.append((time.perf_counter() - start) * 1_000_000)

    clear_user_history(uid)

    avg = statistics.mean(pipeline_times)
    p95 = sorted(pipeline_times)[int(0.95 * len(pipeline_times))]
    target = "✅" if avg < 500 else "⚠️"  # Pipeline target: <500µs avg

    print(f"  {target} Full pipeline (1,000 iterations)")
    print(f"     Avg: {avg:.0f}µs | P95: {p95:.0f}µs")
    print()

    # ---- SUMMARY ----
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    passed = sum(1 for r in results if r["p95_us"] < 100)
    total = len(results)
    print(f"\n  Tests passed: {passed}/{total} (target: p95 < 100µs)")
    print(f"  Pipeline avg: {avg:.0f}µs (target: < 500µs)")

    if passed == total and avg < 500:
        print("\n  🎉 ALL BENCHMARKS PASS! Ready for production.")
    else:
        print("\n  ⚠️  Some benchmarks need attention. Check results above.")

    print()


if __name__ == "__main__":
    main()
