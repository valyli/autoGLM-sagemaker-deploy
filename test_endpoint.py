#!/usr/bin/env python3
"""测试 AutoGLM SageMaker Endpoint"""
import boto3
import json
import sys

# 从 config.json 读取配置
with open('config.json') as f:
    config = json.load(f)

ENDPOINT_NAME = config['endpoint_name']
REGION = config['region']

def test_endpoint(prompt):
    client = boto3.client('sagemaker-runtime', region_name=REGION)
    
    payload = {
        "model": "autoglm-phone-9b",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200
    }
    
    print(f"发送请求: {prompt}")
    response = client.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType='application/json',
        Body=json.dumps(payload)
    )
    
    result = json.loads(response['Body'].read())
    content = result['choices'][0]['message']['content']
    
    print(f"\n模型回复:\n{content}\n")
    return result

if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "打开微信"
    test_endpoint(prompt)
