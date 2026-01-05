"""
Test script to verify Celery is working correctly.

Usage:
    python test_celery.py
"""

import time
from core.celery_app import celery_app, debug_task
from tasks.email import send_welcome_email, send_task_assigned_email


def test_celery_connection():
    """Test 1: Check if Celery can connect to Redis"""
    print("\n" + "=" * 70)
    print("TEST 1: Celery Connection")
    print("=" * 70)

    try:
        # Try to inspect workers
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()

        if active_workers:
            print("✅ Celery is connected!")
            print(f"   Active workers: {list(active_workers.keys())}")
            return True
        else:
            print("❌ No active workers found!")
            print("   Make sure you started the worker:")
            print("   celery -A core.celery_app worker --loglevel=info")
            return False
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        print("   Is Redis running? Check with: redis-cli ping")
        return False


def test_debug_task():
    """Test 2: Run the debug task"""
    print("\n" + "=" * 70)
    print("TEST 2: Debug Task")
    print("=" * 70)

    try:
        print("Sending debug task...")
        result = debug_task.delay()
        print(f"✅ Task queued! Task ID: {result.id}")
        print(f"   Check worker logs to see if it executed")

        # Wait a bit and check result
        print("   Waiting 3 seconds for task to complete...")
        time.sleep(3)

        if result.ready():
            if result.successful():
                print(f"✅ Task completed successfully!")
                print(f"   Result: {result.result}")
                return True
            else:
                print(f"❌ Task failed!")
                print(f"   Error: {result.info}")
                return False
        else:
            print("⚠️  Task still running (might be slow)")
            return True

    except Exception as e:
        print(f"❌ Failed to send task: {e}")
        return False


def test_email_task():
    """Test 3: Send a test email"""
    print("\n" + "=" * 70)
    print("TEST 3: Email Task")
    print("=" * 70)

    try:
        print("Sending test email task...")
        result = send_welcome_email.delay(
            user_email="test@example.com",
            user_name="Test User"
        )
        print(f"✅ Email task queued! Task ID: {result.id}")
        print(f"   Check worker logs to see email details")

        # Wait and check
        print("   Waiting 3 seconds for task to complete...")
        time.sleep(3)

        if result.ready():
            if result.successful():
                print(f"✅ Email task completed!")
                print(f"   Result: {result.result}")
                return True
            else:
                print(f"❌ Email task failed!")
                print(f"   Error: {result.info}")
                return False
        else:
            print("⚠️  Email task still running")
            return True

    except Exception as e:
        print(f"❌ Failed to send email task: {e}")
        return False


def test_registered_tasks():
    """Test 4: Check registered tasks"""
    print("\n" + "=" * 70)
    print("TEST 4: Registered Tasks")
    print("=" * 70)

    try:
        inspect = celery_app.control.inspect()
        registered = inspect.registered()

        if registered:
            print("✅ Found registered tasks:")
            for worker, tasks in registered.items():
                print(f"\n   Worker: {worker}")
                for task in tasks:
                    if task.startswith('tasks.'):
                        print(f"   ✓ {task}")
            return True
        else:
            print("❌ No registered tasks found!")
            return False

    except Exception as e:
        print(f"❌ Failed to get registered tasks: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "🧪 CELERY TEST SUITE ".center(70, "="))
    print("Make sure you have:")
    print("1. Redis running: redis-cli ping")
    print("2. Celery worker running: celery -A core.celery_app worker --loglevel=info")
    print("=" * 70)

    results = {
        "Connection": test_celery_connection(),
        "Debug Task": test_debug_task(),
        "Email Task": test_email_task(),
        "Registered Tasks": test_registered_tasks(),
    }

    print("\n" + "=" * 70)
    print("TEST RESULTS")
    print("=" * 70)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10} {test_name}")

    total_passed = sum(results.values())
    total_tests = len(results)

    print("=" * 70)
    print(f"Total: {total_passed}/{total_tests} tests passed")
    print("=" * 70 + "\n")

    if total_passed == total_tests:
        print("🎉 All tests passed! Celery is working correctly!")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")


if __name__ == "__main__":
    main()