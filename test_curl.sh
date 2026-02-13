#!/bin/bash
# 使用 AWS CLI 调用 SageMaker Endpoint
# 使用方法: ./test_curl.sh "打开微信"

ENDPOINT_NAME="autoglm-phone-9b-20260213-144459"
REGION="us-west-2"
PROMPT="${1:-打开微信}"

echo "📤 发送请求: $PROMPT"
echo "🔗 Endpoint: $ENDPOINT_NAME"
echo ""

# 构造 JSON payload
PAYLOAD=$(cat <<EOF
{
  "model": "autoglm-phone-9b",
  "messages": [{"role": "user", "content": "$PROMPT"}],
  "max_tokens": 200
}
EOF
)

# 使用 AWS CLI 调用
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name "$ENDPOINT_NAME" \
  --region "$REGION" \
  --content-type "application/json" \
  --body "$PAYLOAD" \
  /dev/stdout | jq -r '.choices[0].message.content'
