"""
Scalability test for ML data center location recommendation system
Tests performance with increasing dataset sizes
"""

import subprocess
import time
import json
import csv
from pathlib import Path


def test_dataset_size(num_locations: int) -> dict:
    """Test ML recommendation system with specific dataset size"""
    print(f"\n{'=' * 80}")
    print(f"🧪 Testing with {num_locations} data center locations")
    print(f"{'=' * 80}")

    # Generate dataset
    dataset_file = f"test_{num_locations}_datacenters.csv"

    print(f"1️⃣  Generating dataset...")
    start_gen = time.time()
    result = subprocess.run(
        ["python", "generate_large_dataset.py", str(num_locations), dataset_file],
        capture_output=True,
        text=True
    )
    gen_time = time.time() - start_gen

    if result.returncode != 0:
        print(f"❌ Failed to generate dataset: {result.stderr}")
        return None

    print(f"   ✅ Generated in {gen_time:.2f}s")

    # Test with ML endpoint
    print(f"\n2️⃣  Testing ML recommendation API...")
    start_ml = time.time()

    try:
        result = subprocess.run(
            ["python", "test_ml_endpoint.py", dataset_file],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        ml_time = time.time() - start_ml

        if result.returncode != 0:
            print(f"   ❌ ML test failed: {result.stderr}")
            return None

        print(f"   ✅ Completed in {ml_time:.2f}s")

        # Parse output for processing time
        output_lines = result.stdout.split('\n')
        processing_time = None

        for line in output_lines:
            if "Processing Time:" in line:
                try:
                    processing_time = float(line.split(":")[1].strip().rstrip('s'))
                except:
                    pass

        # Clean up test dataset
        Path(dataset_file).unlink(missing_ok=True)

        return {
            "num_locations": num_locations,
            "generation_time_s": round(gen_time, 2),
            "total_test_time_s": round(ml_time, 2),
            "api_processing_time_s": processing_time,
            "success": True
        }

    except subprocess.TimeoutExpired:
        print(f"   ❌ Test timed out after 5 minutes")
        Path(dataset_file).unlink(missing_ok=True)
        return {
            "num_locations": num_locations,
            "error": "timeout",
            "success": False
        }
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        Path(dataset_file).unlink(missing_ok=True)
        return None


def run_scalability_tests():
    """Run scalability tests with increasing dataset sizes"""
    print("=" * 80)
    print("🚀 ML DATA CENTER LOCATION SYSTEM - SCALABILITY TEST")
    print("=" * 80)
    print("\nTesting performance with increasing dataset sizes...")
    print("This will generate synthetic datasets and test ML recommendations\n")

    # Test sizes: 10, 50, 100, 500, 1000, 1500
    test_sizes = [10, 50, 100, 500, 1000, 1500]

    results = []

    for size in test_sizes:
        result = test_dataset_size(size)
        if result:
            results.append(result)

        # Brief pause between tests
        time.sleep(2)

    # Print summary
    print("\n" + "=" * 80)
    print("📊 SCALABILITY TEST RESULTS")
    print("=" * 80)

    print("\n{:>15} {:>20} {:>20} {:>20}".format(
        "Dataset Size",
        "Generation Time",
        "Total Test Time",
        "API Processing"
    ))
    print("-" * 80)

    for result in results:
        if result["success"]:
            print("{:>15} {:>20} {:>20} {:>20}".format(
                result["num_locations"],
                f"{result['generation_time_s']:.2f}s",
                f"{result['total_test_time_s']:.2f}s",
                f"{result.get('api_processing_time_s', 'N/A')}s" if result.get('api_processing_time_s') else "N/A"
            ))
        else:
            print("{:>15} {:>20}".format(
                result["num_locations"],
                "FAILED/TIMEOUT"
            ))

    # Save results
    with open("scalability_test_results.json", "w") as f:
        json.dump({
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": results
        }, f, indent=2)

    print("\n💾 Results saved to: scalability_test_results.json")

    # Analyze scalability
    successful_results = [r for r in results if r["success"] and r.get("api_processing_time_s")]

    if len(successful_results) >= 2:
        print("\n📈 Scalability Analysis:")

        smallest = successful_results[0]
        largest = successful_results[-1]

        size_ratio = largest["num_locations"] / smallest["num_locations"]
        time_ratio = largest["api_processing_time_s"] / smallest["api_processing_time_s"]

        print(f"   Dataset size increase: {smallest['num_locations']} → {largest['num_locations']} ({size_ratio:.1f}x)")
        print(f"   Processing time increase: {smallest['api_processing_time_s']:.2f}s → {largest['api_processing_time_s']:.2f}s ({time_ratio:.1f}x)")

        if time_ratio < size_ratio * 1.5:
            print(f"   ✅ Good scalability - processing time grows sub-linearly")
        elif time_ratio < size_ratio * 2:
            print(f"   ⚠️  Acceptable scalability - processing time grows near-linearly")
        else:
            print(f"   ❌ Poor scalability - processing time grows super-linearly")

        # Calculate throughput
        throughput_smallest = smallest["num_locations"] / smallest["api_processing_time_s"]
        throughput_largest = largest["num_locations"] / largest["api_processing_time_s"]

        print(f"\n   Throughput (locations/second):")
        print(f"      Small dataset ({smallest['num_locations']}): {throughput_smallest:.1f} loc/s")
        print(f"      Large dataset ({largest['num_locations']}): {throughput_largest:.1f} loc/s")

    print("\n" + "=" * 80)
    print("✅ SCALABILITY TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_scalability_tests()
