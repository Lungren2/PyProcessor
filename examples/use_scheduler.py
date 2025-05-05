"""
Example script demonstrating how to use the scheduler system.

This script shows how to schedule tasks, manage dependencies, and handle task completion.
"""

import os
import sys
import time
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyprocessor.utils.process.scheduler_manager import (
    schedule_task,
    get_task_status,
    wait_for_task,
    cancel_task,
    get_all_tasks,
    get_pending_tasks,
    get_running_tasks,
    get_completed_tasks,
    clear_completed_tasks,
)


# Define some example task functions
def add_numbers(a, b):
    """Add two numbers."""
    print(f"Adding {a} + {b}")
    time.sleep(1)  # Simulate work
    return a + b


def multiply_numbers(a, b):
    """Multiply two numbers."""
    print(f"Multiplying {a} * {b}")
    time.sleep(2)  # Simulate work
    return a * b


def process_result(result):
    """Process a result."""
    print(f"Processing result: {result}")
    time.sleep(1)  # Simulate work
    return f"Processed: {result}"


def task_callback(task_id, success, result_or_error):
    """Callback function for task completion."""
    if success:
        print(f"Task {task_id} completed successfully: {result_or_error}")
    else:
        print(f"Task {task_id} failed: {result_or_error}")


def main():
    """Main function demonstrating scheduler usage."""
    print("Scheduler System Example")
    print("=======================")

    # Schedule a simple task
    print("\n1. Scheduling a simple task")
    task1_id = schedule_task(add_numbers, 5, 3, callback=task_callback)
    print(f"Scheduled task: {task1_id}")

    # Wait for the task to complete
    print("Waiting for task to complete...")
    result = wait_for_task(task1_id)
    print(f"Task result: {result}")

    # Schedule multiple tasks
    print("\n2. Scheduling multiple tasks")
    task2_id = schedule_task(add_numbers, 10, 20, callback=task_callback)
    task3_id = schedule_task(multiply_numbers, 4, 5, callback=task_callback)
    print(f"Scheduled tasks: {task2_id}, {task3_id}")

    # Check task status
    print("\n3. Checking task status")
    time.sleep(0.5)  # Give tasks time to start
    print(f"Task {task2_id} status: {get_task_status(task2_id)['status']}")
    print(f"Task {task3_id} status: {get_task_status(task3_id)['status']}")

    # Wait for all tasks to complete
    print("Waiting for tasks to complete...")
    result2 = wait_for_task(task2_id)
    result3 = wait_for_task(task3_id)
    print(f"Task {task2_id} result: {result2}")
    print(f"Task {task3_id} result: {result3}")

    # Schedule tasks with dependencies
    print("\n4. Scheduling tasks with dependencies")
    task4_id = schedule_task(add_numbers, 7, 8, callback=task_callback)
    task5_id = schedule_task(
        process_result,
        wait_for_task(task4_id),
        dependencies=[task4_id],
        callback=task_callback,
    )
    print(f"Scheduled tasks with dependencies: {task4_id} -> {task5_id}")

    # Wait for the final task to complete
    print("Waiting for tasks to complete...")
    result5 = wait_for_task(task5_id)
    print(f"Final result: {result5}")

    # Schedule tasks with priorities
    print("\n5. Scheduling tasks with priorities")
    task6_id = schedule_task(add_numbers, 1, 2, priority=1, callback=task_callback)
    task7_id = schedule_task(add_numbers, 3, 4, priority=10, callback=task_callback)
    task8_id = schedule_task(add_numbers, 5, 6, priority=5, callback=task_callback)
    print(
        f"Scheduled tasks with priorities: {task6_id} (1), {task7_id} (10), {task8_id} (5)"
    )

    # Wait for all tasks to complete
    print("Waiting for tasks to complete...")
    wait_for_task(task6_id)
    wait_for_task(task7_id)
    wait_for_task(task8_id)

    # Cancel a task
    print("\n6. Cancelling a task")
    task9_id = schedule_task(multiply_numbers, 10, 10, callback=task_callback)
    print(f"Scheduled task: {task9_id}")
    time.sleep(0.1)  # Give task time to start
    cancelled = cancel_task(task9_id)
    print(f"Task cancelled: {cancelled}")

    # List tasks
    print("\n7. Listing tasks")
    all_tasks = get_all_tasks()
    pending_tasks = get_pending_tasks()
    running_tasks = get_running_tasks()
    completed_tasks = get_completed_tasks()
    print(f"Total tasks: {len(all_tasks)}")
    print(f"Pending tasks: {len(pending_tasks)}")
    print(f"Running tasks: {len(running_tasks)}")
    print(f"Completed tasks: {len(completed_tasks)}")

    # Clear completed tasks
    print("\n8. Clearing completed tasks")
    cleared = clear_completed_tasks()
    print(f"Cleared {cleared} completed tasks")

    print("\nScheduler example completed")


if __name__ == "__main__":
    main()
