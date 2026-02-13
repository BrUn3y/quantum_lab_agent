#!/usr/bin/env python3
"""Test script to check IBM Quantum backend availability"""

import os
from dotenv import load_dotenv
from qiskit_ibm_runtime import QiskitRuntimeService

# Load environment variables
load_dotenv()

def test_quantum_status():
    """Test the quantum status functionality"""
    try:
        print("🔬 Testing IBM Quantum Status Tool...")
        print("=" * 60)
        
        # Initialize service
        token = os.getenv('QISKIT_IBM_TOKEN')
        if not token:
            print("❌ ERROR: QISKIT_IBM_TOKEN not found in environment")
            return
        
        print(f"✅ Token found: {token[:10]}...")
        print("\n📡 Connecting to IBM Quantum Platform...")
        
        service = QiskitRuntimeService(channel="ibm_quantum_platform")
        print("✅ Connected successfully!")
        
        # Test 1: Get all backends (no filters)
        print("\n" + "=" * 60)
        print("TEST 1: All backends (no filters)")
        print("=" * 60)
        all_backends = service.backends()
        print(f"Total backends found: {len(all_backends)}")
        for backend in all_backends:
            print(f"  - {backend.name} (simulator: {backend.simulator})")
        
        # Test 2: Only operational backends
        print("\n" + "=" * 60)
        print("TEST 2: Operational backends only")
        print("=" * 60)
        operational_backends = service.backends(operational=True)
        print(f"Operational backends found: {len(operational_backends)}")
        for backend in operational_backends:
            status = backend.status()
            print(f"  - {backend.name}")
            print(f"    Operational: {status.operational}")
            print(f"    Pending jobs: {status.pending_jobs if hasattr(status, 'pending_jobs') else 'N/A'}")
        
        # Test 3: Only real hardware (no simulators)
        print("\n" + "=" * 60)
        print("TEST 3: Real hardware only (no simulators)")
        print("=" * 60)
        hardware_backends = service.backends(simulator=False, operational=True)
        print(f"Hardware backends found: {len(hardware_backends)}")
        for backend in hardware_backends:
            status = backend.status()
            print(f"  - {backend.name}")
            print(f"    Qubits: {backend.num_qubits if hasattr(backend, 'num_qubits') else 'N/A'}")
            print(f"    Operational: {status.operational}")
            print(f"    Pending jobs: {status.pending_jobs if hasattr(status, 'pending_jobs') else 'N/A'}")
        
        # Test 4: Check if any backend is available
        print("\n" + "=" * 60)
        print("TEST 4: Availability check")
        print("=" * 60)
        if not hardware_backends:
            print("⚠️  WARNING: No hardware backends available!")
            print("This could mean:")
            print("  1. IBM Quantum is experiencing issues")
            print("  2. Your account doesn't have access to hardware")
            print("  3. All backends are temporarily offline")
        else:
            print(f"✅ {len(hardware_backends)} hardware backend(s) available")
            
            # Find least busy
            least_busy = min(
                hardware_backends,
                key=lambda b: b.status().pending_jobs if hasattr(b.status(), 'pending_jobs') else float('inf')
            )
            pending = least_busy.status().pending_jobs if hasattr(least_busy.status(), 'pending_jobs') else 0
            print(f"💡 Least busy: {least_busy.name} with {pending} jobs in queue")
        
        print("\n" + "=" * 60)
        print("✅ Test completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_quantum_status()

# Made with Bob
