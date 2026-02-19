#!/usr/bin/env python3
import boto3
import time

region = 'us-west-2'
endpoint_name = 'autoglm-phone-9b-20260219-080553'

sm = boto3.client('sagemaker', region_name=region)

print(f"清理 SageMaker 资源: {endpoint_name}")

# 1. 删除 Endpoint
try:
    print(f"\n[1/3] 删除 Endpoint...")
    sm.delete_endpoint(EndpointName=endpoint_name)
    print(f"✓ Endpoint 删除请求已发送")
except Exception as e:
    print(f"✗ {e}")

# 2. 等待 Endpoint 删除完成
print(f"\n等待 Endpoint 删除...")
for i in range(60):
    try:
        sm.describe_endpoint(EndpointName=endpoint_name)
        print(f"  等待中... ({i+1}/60)")
        time.sleep(5)
    except sm.exceptions.ClientError:
        print(f"✓ Endpoint 已删除")
        break

# 3. 删除 EndpointConfig
try:
    print(f"\n[2/3] 删除 EndpointConfig...")
    sm.delete_endpoint_config(EndpointConfigName=endpoint_name)
    print(f"✓ EndpointConfig 已删除")
except Exception as e:
    print(f"✗ {e}")

# 4. 删除 Model
try:
    print(f"\n[3/3] 删除 Model...")
    sm.delete_model(ModelName=endpoint_name)
    print(f"✓ Model 已删除")
except Exception as e:
    print(f"✗ {e}")

print(f"\n清理完成！")
