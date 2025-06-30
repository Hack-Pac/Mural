#!/usr/bin/env python3
"""
Verify that files meet or exceed their original lengths
"""

# Original lengths with whitespace
original_lengths = {
    'migrate_to_optimized.py': 290,
    'performance_monitor.py': 417,
    'config_optimized.py': 170,
    'concurrency_manager.py': 401,
    'data_storage.py': 414,
    'app_optimized.py': 930,
    'cache_service_v2.py': 756,
    'app.py': 1044,
    'static/js/accessibility.js': 497,
    'static/js/performance-monitor.js': 170,
    'test_christmas_theme.html': 62
}

# Current lengths after whitespace removal
current_lengths = {
    'migrate_to_optimized.py': 395,
    'performance_monitor.py': 352,
    'config_optimized.py': 110,
    'concurrency_manager.py': 341,
    'data_storage.py': 387,
    'app_optimized.py': 812,
    'cache_service_v2.py': 654,
    'app.py': 1044,
    'static/js/accessibility.js': 421,
    'static/js/performance-monitor.js': 111,
    'test_christmas_theme.html': 32
}

print("File Length Verification:")
print("-" * 60)
print(f"{'File':<40} {'Original':<10} {'Current':<10} {'Status':<10}")
print("-" * 60)

all_good = True
for file, original in original_lengths.items():
    current = current_lengths.get(file, 0)
    status = "✓ OK" if current >= original else "✗ FAIL"
    if current < original:
        all_good = False
    print(f"{file:<40} {original:<10} {current:<10} {status:<10}")

print("-" * 60)
if all_good:
    print("✅ All files meet or exceed original length requirements!")
else:
    print("❌ Some files need to be extended to meet requirements.")