#!/usr/bin/env python3
import boto3
from datetime import datetime, timedelta

endpoint_arn = "arn:aws:sagemaker:us-west-2:210126446796:endpoint/autoglm-phone-9b-20260219-081841"
endpoint_name = endpoint_arn.split('/')[-1]
region = 'us-west-2'

sm_client = boto3.client('sagemaker', region_name=region)
logs_client = boto3.client('logs', region_name=region)

# Get endpoint details
print(f"Checking endpoint: {endpoint_name}\n")
endpoint = sm_client.describe_endpoint(EndpointName=endpoint_name)
print(f"Status: {endpoint['EndpointStatus']}")
print(f"Creation Time: {endpoint['CreationTime']}")

if 'FailureReason' in endpoint:
    print(f"\nFailure Reason: {endpoint['FailureReason']}")

# Get log group name
log_group = f"/aws/sagemaker/Endpoints/{endpoint_name}"

try:
    # Get log streams
    streams = logs_client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=5
    )
    
    print(f"\n{'='*80}")
    print(f"Recent Log Streams:")
    print(f"{'='*80}\n")
    
    for stream in streams['logStreams']:
        stream_name = stream['logStreamName']
        print(f"\n--- Log Stream: {stream_name} ---\n")
        
        # Get log events
        events = logs_client.get_log_events(
            logGroupName=log_group,
            logStreamName=stream_name,
            startFromHead=False,
            limit=100
        )
        
        for event in events['events']:
            timestamp = datetime.fromtimestamp(event['timestamp']/1000)
            print(f"[{timestamp}] {event['message']}")
            
except logs_client.exceptions.ResourceNotFoundException:
    print(f"\nLog group not found: {log_group}")
    print("Logs may not be available yet or endpoint hasn't started.")
except Exception as e:
    print(f"\nError retrieving logs: {e}")
