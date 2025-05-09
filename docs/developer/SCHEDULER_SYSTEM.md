# Scheduler System in PyProcessor

This document describes the scheduler system in PyProcessor, including the centralized `SchedulerManager` class, task scheduling, and task management.

## Overview

PyProcessor provides a centralized scheduler system through the `SchedulerManager` class in the `pyprocessor.utils.scheduler_manager` module. This class provides a consistent interface for scheduling and managing tasks across the application.

The scheduler system is designed to:

- Provide a consistent way to schedule and execute tasks
- Support task prioritization and dependencies
- Track task status and results
- Handle task cancellation and cleanup
- Integrate with the process management system

## SchedulerManager

The `SchedulerManager` class is a singleton that provides the following features:

- Task scheduling and execution
- Task prioritization and dependencies
- Task monitoring and status tracking
- Task cancellation and cleanup

### Getting the Scheduler Manager

```python
from pyprocessor.utils.scheduler_manager import get_scheduler_manager

# Get the scheduler manager
scheduler_manager = get_scheduler_manager()
```

## Task Scheduling

### Scheduling Tasks

```python
from pyprocessor.utils.scheduler_manager import schedule_task

# Define a task function
def process_file(file_path):
    # Process the file
    return f"Processed {file_path}"

# Schedule a task
task_id = schedule_task(process_file, "file.mp4")

# Schedule a task with priority
task_id = schedule_task(process_file, "file.mp4", priority=10)

# Schedule a task with dependencies
task_id = schedule_task(process_file, "file.mp4", dependencies=["other_task_id"])

# Schedule a task with a callback
def task_callback(task_id, success, result_or_error):
    if success:
        print(f"Task {task_id} completed successfully: {result_or_error}")
    else:
        print(f"Task {task_id} failed: {result_or_error}")

task_id = schedule_task(process_file, "file.mp4", callback=task_callback)
```

### Task Dependencies

Tasks can depend on other tasks, which means they will only be executed after their dependencies have completed:

```python
# Define task functions
def prepare_file(file_path):
    # Prepare the file
    return f"Prepared {file_path}"

def process_file(file_path):
    # Process the file
    return f"Processed {file_path}"

def finalize_file(file_path):
    # Finalize the file
    return f"Finalized {file_path}"

# Schedule tasks with dependencies
prepare_task_id = schedule_task(prepare_file, "file.mp4")
process_task_id = schedule_task(process_file, "file.mp4", dependencies=[prepare_task_id])
finalize_task_id = schedule_task(finalize_file, "file.mp4", dependencies=[process_task_id])
```

### Task Prioritization

Tasks can be prioritized, which means they will be executed before lower-priority tasks:

```python
# Schedule tasks with different priorities
low_priority_task_id = schedule_task(process_file, "file1.mp4", priority=1)
medium_priority_task_id = schedule_task(process_file, "file2.mp4", priority=5)
high_priority_task_id = schedule_task(process_file, "file3.mp4", priority=10)
```

## Task Management

### Getting Task Status

```python
from pyprocessor.utils.scheduler_manager import get_task_status

# Get the status of a task
status = get_task_status(task_id)
print(f"Task status: {status['status']}")
```

### Waiting for Tasks

```python
from pyprocessor.utils.scheduler_manager import wait_for_task

# Wait for a task to complete
result = wait_for_task(task_id)
print(f"Task result: {result}")

# Wait for a task with a timeout
result = wait_for_task(task_id, timeout=10)
if result is None:
    print("Task timed out")
else:
    print(f"Task result: {result}")
```

### Cancelling Tasks

```python
from pyprocessor.utils.scheduler_manager import cancel_task

# Cancel a task
cancelled = cancel_task(task_id)
if cancelled:
    print("Task cancelled")
else:
    print("Task not found or already completed")
```

### Listing Tasks

```python
from pyprocessor.utils.scheduler_manager import (
    get_all_tasks,
    get_pending_tasks,
    get_running_tasks,
    get_completed_tasks,
)

# Get all tasks
all_tasks = get_all_tasks()
print(f"Total tasks: {len(all_tasks)}")

# Get pending tasks
pending_tasks = get_pending_tasks()
print(f"Pending tasks: {len(pending_tasks)}")

# Get running tasks
running_tasks = get_running_tasks()
print(f"Running tasks: {len(running_tasks)}")

# Get completed tasks
completed_tasks = get_completed_tasks()
print(f"Completed tasks: {len(completed_tasks)}")
```

### Cleaning Up Tasks

```python
from pyprocessor.utils.scheduler_manager import clear_completed_tasks

# Clear completed tasks
cleared = clear_completed_tasks()
print(f"Cleared {cleared} completed tasks")
```

## Scheduler Control

### Starting and Stopping the Scheduler

```python
from pyprocessor.utils.scheduler_manager import start_scheduler, stop_scheduler

# Start the scheduler
start_scheduler()

# Stop the scheduler
stop_scheduler()
```

## Integration with Process Management

The scheduler system integrates with the process management system to execute tasks in separate processes:

```python
from pyprocessor.utils.scheduler_manager import schedule_task
from pyprocessor.utils.process_manager import get_process_manager

# Get the process manager
process_manager = get_process_manager()

# Create a process pool
pool_id = process_manager.create_process_pool(max_workers=4)

# Schedule a task to be executed in the process pool
task_id = schedule_task(process_file, "file.mp4", executor_id=pool_id)
```

## Best Practices

1. **Use Task Dependencies**: Use task dependencies to ensure tasks are executed in the correct order.
2. **Use Task Priorities**: Use task priorities to ensure important tasks are executed first.
3. **Use Task Callbacks**: Use task callbacks to handle task completion and errors.
4. **Clean Up Completed Tasks**: Regularly clean up completed tasks to free up memory.
5. **Handle Task Errors**: Always handle task errors in your callback functions.
6. **Set Timeouts**: Always set timeouts when waiting for tasks to avoid hanging.
7. **Use Process Pools**: Use process pools for CPU-bound tasks and thread pools for I/O-bound tasks.
8. **Monitor Task Status**: Regularly check the status of tasks to ensure they are running as expected.
9. **Limit Concurrency**: Limit the number of concurrent tasks to avoid overloading the system.
10. **Graceful Shutdown**: Always stop the scheduler gracefully when shutting down the application.

## Example: Video Processing Pipeline

Here's an example of using the scheduler system to implement a video processing pipeline:

```python
from pyprocessor.utils.scheduler_manager import schedule_task, wait_for_task

# Define task functions
def extract_audio(video_path):
    # Extract audio from video
    audio_path = video_path.replace(".mp4", ".mp3")
    # ... extraction logic ...
    return audio_path

def transcribe_audio(audio_path):
    # Transcribe audio to text
    text_path = audio_path.replace(".mp3", ".txt")
    # ... transcription logic ...
    return text_path

def analyze_text(text_path):
    # Analyze text for sentiment
    # ... analysis logic ...
    return {"sentiment": "positive", "confidence": 0.85}

# Define callback function
def task_callback(task_id, success, result_or_error):
    if success:
        print(f"Task {task_id} completed successfully: {result_or_error}")
    else:
        print(f"Task {task_id} failed: {result_or_error}")

# Schedule tasks with dependencies
video_path = "video.mp4"
extract_task_id = schedule_task(extract_audio, video_path, callback=task_callback)
transcribe_task_id = schedule_task(
    transcribe_audio, wait_for_task(extract_task_id),
    dependencies=[extract_task_id], callback=task_callback
)
analyze_task_id = schedule_task(
    analyze_text, wait_for_task(transcribe_task_id),
    dependencies=[transcribe_task_id], callback=task_callback
)

# Wait for the final result
result = wait_for_task(analyze_task_id)
print(f"Final result: {result}")
```

## Troubleshooting

If you encounter issues with the scheduler system, try the following:

1. **Check Task Status**: Use `get_task_status` to check the status of your tasks.
2. **Check Task Dependencies**: Make sure your task dependencies are correct.
3. **Check Task Priorities**: Make sure your task priorities are set correctly.
4. **Check Task Callbacks**: Make sure your task callbacks are handling errors correctly.
5. **Check Process Manager**: Make sure the process manager is working correctly.
6. **Check Logs**: Look for error messages in the application logs.
7. **Restart Scheduler**: Try stopping and starting the scheduler.
8. **Clear Completed Tasks**: Try clearing completed tasks to free up memory.
9. **Reduce Concurrency**: Try reducing the number of concurrent tasks.
10. **Increase Timeouts**: Try increasing timeouts when waiting for tasks.
