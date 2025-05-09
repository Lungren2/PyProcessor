# Process Management in PyProcessor

This document describes the process management system in PyProcessor, including the centralized `ProcessManager` class, process pool management, and inter-process communication.

## Overview

PyProcessor provides a centralized process management system through the `ProcessManager` class in the `pyprocessor.utils.process_manager` module. This class provides a consistent interface for process-related operations across the application.

The process management system is designed to:

- Provide a consistent way to create and manage processes
- Track process status and output
- Manage process pools for parallel execution
- Facilitate inter-process communication
- Handle process termination and cleanup

## ProcessManager

The `ProcessManager` class is a singleton that provides the following features:

- Process creation and execution
- Process monitoring and status tracking
- Process termination and cleanup
- Process pool management
- Inter-process communication

### Getting the Process Manager

```python
from pyprocessor.utils.process_manager import get_process_manager

# Get the process manager
process_manager = get_process_manager()
```

## Basic Process Management

### Running Processes

```python
from pyprocessor.utils.process_manager import run_process, run_process_async

# Run a process and wait for it to complete
result = run_process(
    cmd=["ffmpeg", "-i", "input.mp4", "output.mp4"],
    cwd="/path/to/working/dir",
    timeout=60  # Timeout in seconds
)

# Check the result
if result["returncode"] == 0:
    print("Process completed successfully")
    print(f"Output: {result['stdout']}")
else:
    print(f"Process failed with return code {result['returncode']}")
    print(f"Error: {result['stderr']}")

# Run a process asynchronously
process_id = run_process_async(
    cmd=["ffmpeg", "-i", "input.mp4", "output.mp4"],
    cwd="/path/to/working/dir"
)

# Check the status later
status = get_process_status(process_id)
print(f"Process status: {status['status']}")
```

### Managing Processes

```python
from pyprocessor.utils.process_manager import get_process_status, terminate_process, list_processes, cleanup_processes

# Get the status of a process
status = get_process_status(process_id)
print(f"Process status: {status['status']}")

# Terminate a process
terminated = terminate_process(process_id)
if terminated:
    print("Process terminated")
else:
    print("Process not found or already completed")

# List all processes
processes = list_processes()
for process in processes:
    print(f"Process {process['process_id']}: {process['status']}")

# Clean up completed processes
cleaned_up = cleanup_processes()
print(f"Cleaned up {cleaned_up} processes")
```

## Process Pool Management

PyProcessor provides process pool management for parallel execution of tasks:

```python
from pyprocessor.utils.process_manager import create_process_pool, submit_task, get_task_result

# Create a process pool
pool_id = create_process_pool(max_workers=4)

# Define a task function
def process_file(file_path):
    # Process the file
    return f"Processed {file_path}"

# Submit tasks to the pool
task_ids = []
for file_path in ["file1.mp4", "file2.mp4", "file3.mp4"]:
    task_id = submit_task(process_file, file_path, executor_id=pool_id)
    task_ids.append(task_id)

# Get the results
for task_id in task_ids:
    result = get_task_result(task_id)
    print(result)

# Shutdown the pool when done
shutdown_executor(pool_id)
```

### Thread Pools

PyProcessor also provides thread pools for I/O-bound tasks:

```python
from pyprocessor.utils.process_manager import create_thread_pool, submit_task

# Create a thread pool
pool_id = create_thread_pool(max_workers=10)

# Define a task function
def download_file(url):
    # Download the file
    return f"Downloaded {url}"

# Submit tasks to the pool
task_ids = []
for url in ["http://example.com/file1", "http://example.com/file2"]:
    task_id = submit_task(download_file, url, executor_id=pool_id)
    task_ids.append(task_id)

# Get the results
for task_id in task_ids:
    result = get_task_result(task_id)
    print(result)

# Shutdown the pool when done
shutdown_executor(pool_id)
```

### Default Pools

PyProcessor provides default process and thread pools:

```python
from pyprocessor.utils.process_manager import get_default_process_pool, get_default_thread_pool, submit_task

# Get the default process pool
process_pool_id = get_default_process_pool()

# Get the default thread pool
thread_pool_id = get_default_thread_pool()

# Submit a task to the default process pool
task_id = submit_task(process_file, "file.mp4")  # Uses default process pool

# Submit a task to the default thread pool
task_id = submit_task(download_file, "http://example.com/file", executor_id=thread_pool_id)
```

### Task Management

PyProcessor provides methods for managing tasks:

```python
from pyprocessor.utils.process_manager import get_task_status, cancel_task

# Get the status of a task
status = get_task_status(task_id)
print(f"Task status: {status['status']}")

# Cancel a task
cancelled = cancel_task(task_id)
if cancelled:
    print("Task cancelled")
else:
    print("Task not found or already completed")
```

## Inter-Process Communication (IPC)

PyProcessor provides inter-process communication mechanisms:

### Queues

```python
from pyprocessor.utils.process_manager import create_queue, put_queue_item, get_queue_item

# Create a queue
queue_id = create_queue(maxsize=10)

# Put items in the queue
put_queue_item(queue_id, "item1")
put_queue_item(queue_id, {"key": "value"})

# Get items from the queue
item1 = get_queue_item(queue_id)
item2 = get_queue_item(queue_id)

# Check queue status
size = get_queue_size(queue_id)
is_empty = is_queue_empty(queue_id)
is_full = is_queue_full(queue_id)

# Clear the queue
cleared = clear_queue(queue_id)
print(f"Cleared {cleared} items from the queue")

# Delete the queue when done
delete_queue(queue_id)
```

### Shared Values

```python
from pyprocessor.utils.process_manager import create_shared_value, get_shared_value, set_shared_value

# Create a shared integer value
value_id = create_shared_value(value_type="i", initial_value=0)

# Get the value
value = get_shared_value(value_id)
print(f"Value: {value}")

# Set the value
set_shared_value(value_id, 42)

# Create a shared boolean value
bool_id = create_shared_value(value_type="b", initial_value=False)

# Create a shared double value
double_id = create_shared_value(value_type="d", initial_value=3.14)
```

### Events

```python
from pyprocessor.utils.process_manager import create_event, set_event, clear_event, wait_for_event, is_event_set

# Create an event
event_id = create_event()

# Set the event
set_event(event_id)

# Check if the event is set
if is_event_set(event_id):
    print("Event is set")

# Clear the event
clear_event(event_id)

# Wait for the event to be set
if wait_for_event(event_id, timeout=10):
    print("Event was set")
else:
    print("Timeout waiting for event")
```

### Locks

```python
from pyprocessor.utils.process_manager import create_lock, acquire_lock, release_lock, lock_context

# Create a lock
lock_id = create_lock()

# Acquire the lock
if acquire_lock(lock_id, timeout=5):
    try:
        # Do something with the lock
        print("Lock acquired")
    finally:
        # Release the lock
        release_lock(lock_id)

# Use the lock context manager
with lock_context(lock_id, timeout=5):
    # Do something with the lock
    print("Lock acquired")
    # Lock is automatically released when the context exits
```

## Best Practices

1. **Use the Process Manager**: Always use the `ProcessManager` for process-related operations to ensure consistent tracking and management.

2. **Clean Up Resources**: Always clean up resources when done, including terminating processes, shutting down executors, and deleting queues.

3. **Use Process Pools**: Use process pools for CPU-bound tasks and thread pools for I/O-bound tasks.

4. **Set Timeouts**: Always set timeouts when running processes or waiting for events to avoid hanging.

5. **Handle Errors**: Always handle errors when running processes or submitting tasks.

6. **Use IPC Mechanisms**: Use the appropriate IPC mechanism for your needs:
   - Queues for passing data between processes
   - Shared values for sharing simple values between processes
   - Events for signaling between processes
   - Locks for synchronizing access to shared resources

7. **Monitor Process Status**: Regularly check the status of processes and tasks to ensure they are running as expected.

8. **Limit Concurrency**: Limit the number of concurrent processes and tasks to avoid overloading the system.

## Integration with Other Systems

The process management system works closely with other systems in PyProcessor:

- **Path Management**: Process working directories are normalized using the path management system.
- **Logging**: Process operations are logged using the logging system.
- **Error Handling**: Process errors are handled by the error handling system.

```python
from pyprocessor.utils.process_manager import run_process
from pyprocessor.utils.path_manager import normalize_path

# Run a process with a normalized working directory
result = run_process(
    cmd=["ffmpeg", "-i", "input.mp4", "output.mp4"],
    cwd=normalize_path("/path/to/working/dir")
)
```
