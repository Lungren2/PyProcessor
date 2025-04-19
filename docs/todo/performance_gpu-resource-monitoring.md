# Implement GPU Resource Monitoring

## Description
Add GPU resource monitoring capabilities to track and manage GPU usage when using hardware acceleration encoders like h264_nvenc and hevc_nvenc.

## Acceptance Criteria
- [ ] Detect available GPUs and their capabilities
- [ ] Monitor GPU memory usage during encoding
- [ ] Monitor GPU utilization percentage
- [ ] Implement throttling when GPU resources are constrained
- [ ] Add GPU metrics to the logging system
- [ ] Update resource calculator to consider GPU resources

## Related Components
- `pyprocessor/utils/process/resource_manager.py`
- `pyprocessor/utils/process/resource_calculator.py`
- `pyprocessor/processing/encoder.py`

## Dependencies
- Resource monitoring system (completed)

## Priority
Medium

## Estimated Effort
Medium (3-5 days)
