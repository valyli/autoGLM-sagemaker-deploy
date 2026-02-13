# 通过 API Gateway 暴露 SageMaker Endpoint

## 方案：Lambda + API Gateway

### 1. 创建 Lambda 函数

```python
# lambda_function.py
import json
import boto3

ENDPOINT_NAME = "autoglm-phone-9b-20260213-144459"
REGION = "us-west-2"

def lambda_handler(event, context):
    """Lambda 函数处理 API Gateway 请求"""
    
    # 解析请求
    try:
        body = json.loads(event.get('body', '{}'))
        prompt = body.get('prompt', '打开微信')
    except:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid JSON'})
        }
    
    # 调用 SageMaker
    client = boto3.client('sagemaker-runtime', region_name=REGION)
    
    payload = {
        "model": "autoglm-phone-9b",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200
    }
    
    response = client.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType='application/json',
        Body=json.dumps(payload)
    )
    
    result = json.loads(response['Body'].read())
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'response': result['choices'][0]['message']['content'],
            'usage': result.get('usage', {})
        }, ensure_ascii=False)
    }
```

### 2. 部署步骤

```bash
# 1. 创建 Lambda 函数
aws lambda create-function \
  --function-name autoglm-proxy \
  --runtime python3.9 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-sagemaker-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --region us-west-2

# 2. 创建 API Gateway
aws apigatewayv2 create-api \
  --name autoglm-api \
  --protocol-type HTTP \
  --target arn:aws:lambda:us-west-2:YOUR_ACCOUNT:function:autoglm-proxy

# 3. 获取 API URL
# 输出类似: https://abc123.execute-api.us-west-2.amazonaws.com
```

### 3. 浏览器测试

```html
<!DOCTYPE html>
<html>
<head>
    <title>AutoGLM Test</title>
</head>
<body>
    <h1>AutoGLM Endpoint 测试</h1>
    <input id="prompt" type="text" placeholder="输入指令" value="打开微信">
    <button onclick="test()">发送</button>
    <pre id="result"></pre>
    
    <script>
    async function test() {
        const prompt = document.getElementById('prompt').value;
        const result = document.getElementById('result');
        
        result.textContent = '请求中...';
        
        const response = await fetch('YOUR_API_GATEWAY_URL', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({prompt: prompt})
        });
        
        const data = await response.json();
        result.textContent = JSON.stringify(data, null, 2);
    }
    </script>
</body>
</html>
```

### 4. curl 测试

```bash
curl -X POST https://YOUR_API_URL \
  -H "Content-Type: application/json" \
  -d '{"prompt": "打开微信"}'
```

## 成本

- Lambda: 前 100 万次请求免费
- API Gateway: $1/百万次请求
- SageMaker Endpoint: $0.503/小时（已有）

## 安全建议

1. 添加 API Key 认证
2. 限制请求频率
3. 使用 VPC 内网访问
4. 启用 CloudWatch 日志
