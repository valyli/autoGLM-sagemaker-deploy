#!/usr/bin/env python3
"""
本地测试 AutoGLM SageMaker Endpoint
使用方法: python3 test_local.py "打开微信"
"""
import boto3
import json
import sys

# 配置信息
ENDPOINT_NAME = "autoglm-phone-9b-20260213-144459"
REGION = "us-west-2"

def test_endpoint(prompt):
    """测试 SageMaker Endpoint"""
    try:
        client = boto3.client('sagemaker-runtime', region_name=REGION)
        
        payload = {
            "model": "autoglm-phone-9b",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200
        }
        
        print(f"📤 发送请求: {prompt}")
        print(f"🔗 Endpoint: {ENDPOINT_NAME}")
        print(f"🌍 Region: {REGION}\n")
        
        response = client.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        
        result = json.loads(response['Body'].read())
        content = result['choices'][0]['message']['content']
        
        print(f"✅ 模型回复:\n{content}\n")
        
        # 显示使用统计
        usage = result.get('usage', {})
        print(f"📊 Token 使用: {usage.get('total_tokens', 0)} "
              f"(输入: {usage.get('prompt_tokens', 0)}, "
              f"输出: {usage.get('completion_tokens', 0)})")
        
        return result
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        print("\n请确保:")
        print("1. 已配置 AWS 凭证 (aws configure)")
        print("2. 凭证有 SageMaker 调用权限")
        print("3. Endpoint 正在运行")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python3 test_local.py \"你的指令\"")
        print("示例: python3 test_local.py \"打开微信\"")
        sys.exit(1)
    
    prompt = sys.argv[1]
    test_endpoint(prompt)
