"""
Simple test script for BL531API
"""
from BL531API import bl531
import json

print("\n" + "="*80)
print("BL531 Beamline Control API - Test Script")
print("="*80)

# Test 1: Count plan with diode
print("\n1️⃣  Testing count plan with diode...")
try:
    result = bl531.count(detectors=["diode"], num=1)
    print(f"   ✅ Success!")
    print(f"   run_uid: {result.run_uid}")
    print(f"   plan_name: {result.plan_name}")
    print(f"   timestamp: {result.timestamp}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Count plan with both detectors
print("\n2️⃣  Testing count plan with diode and det...")
try:
    result = bl531.count(detectors=["diode", "det"], num=1)
    print(f"   ✅ Success!")
    print(f"   run_uid: {result.run_uid}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Scan plan
print("\n3️⃣  Testing scan plan...")
try:
    result = bl531.scan(
        detectors=["diode"],
        motor="hexapod_motor_Ty",
        start=0,
        stop=0.3,
        num=5
    )
    print(f"   ✅ Success!")
    print(f"   run_uid: {result.run_uid}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# # Test 4: Alignment plan
# print("\n4️⃣  Testing alignment plan...")
# try:
#     result = bl531.automatic_gisaxs_alignment()
#     print(f"   ✅ Success!")
#     print(f"   run_uid: {result.run_uid}")
# except Exception as e:
#     print(f"   ❌ Error: {e}")

# Test 4:  
print("\n5️⃣  Testing non existent detector...")
try:
    result = bl531.scan(
        detectors=["non-existing"],
        motor="hexapod_motor_Ry",
        start=-0.5,
        stop=0.5,
        num=5
    )
    print(f"   ✅ Success!")
    print(f"   run_uid: {result.run_uid}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 5: Scan with multiple detectors
print("\n5️⃣  Testing scan with multiple detectors...")
try:
    result = bl531.scan(
        detectors=["diode", "det"],
        motor="hexapod_motor_Ry",
        start=-0.5,
        stop=0.5,
        num=5
    )
    print(f"   ✅ Success!")
    print(f"   run_uid: {result.run_uid}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "="*80)
print("Test script completed")
print("="*80 + "\n")

