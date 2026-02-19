#!/usr/bin/env python3
"""测试 AutoGLM SageMaker Endpoint"""
import boto3
import json
import sys
import argparse
import base64
import os

# 解析命令行参数
parser = argparse.ArgumentParser(description='测试 SageMaker Endpoint')
parser.add_argument('--config', default='config.json', help='配置文件路径 (默认: config.json)')
parser.add_argument('--image', default='test/macos-desktop.jpg', help='测试图片路径')
parser.add_argument('prompt', nargs='?', default='打开微信', help='测试提示词')
args = parser.parse_args()

# 从配置文件读取
try:
    with open(args.config) as f:
        config = json.load(f)
except FileNotFoundError:
    print(f"❌ 配置文件不存在: {args.config}")
    print("\n可用配置:")
    import os
    if os.path.exists('configs'):
        for f in os.listdir('configs'):
            if f.endswith('.json'):
                print(f"  configs/{f}")
    sys.exit(1)

ENDPOINT_NAME = config['endpoint_name']
REGION = config['region']
PRESET = config.get('preset', 'unknown')
MODEL_ID = config.get('model_id', 'unknown')
SERVED_MODEL_NAME = config.get('served_model_name', 'autoglm-phone-9b')

def test_endpoint(prompt, image_path=None):
    client = boto3.client('sagemaker-runtime', region_name=REGION)
    
    # 构建消息内容
    content = []
    if image_path and os.path.exists(image_path):
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}})
        content.append({"type": "text", "text": prompt})
    else:
        content = prompt
    
    payload = {
        "model": SERVED_MODEL_NAME,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 200
    }
    
    print(f"📦 预设: {PRESET}")
    print(f"🤖 模型: {MODEL_ID}")
    print(f"🔗 Endpoint: {ENDPOINT_NAME}")
    print(f"🌍 区域: {REGION}")
    if image_path and os.path.exists(image_path):
        print(f"🖼️  图片: {image_path}")
    print(f"\n📤 发送请求: {prompt}\n")
    
    response = client.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType='application/json',
        Body=json.dumps(payload)
    )
    
    result = json.loads(response['Body'].read())
    
    # 调试: 打印原始响应
    if 'choices' not in result:
        print(f"⚠️  响应格式异常，原始响应:\n{json.dumps(result, indent=2, ensure_ascii=False)}\n")
        return result
    
    content = result['choices'][0]['message']['content']
    
    print(f"✅ 模型回复:\n{content}\n")
    
    # 显示使用统计
    usage = result.get('usage', {})
    print(f"📊 Token 使用: {usage.get('total_tokens', 0)} "
          f"(输入: {usage.get('prompt_tokens', 0)}, "
          f"输出: {usage.get('completion_tokens', 0)})")
    
    return result

if __name__ == "__main__":
    test_endpoint(args.prompt, args.image)
