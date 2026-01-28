# AutoGLM-Phone-9B SageMaker 部署

将 [AutoGLM-Phone-9B](https://huggingface.co/zai-org/AutoGLM-Phone-9B) 视觉语言模型部署到 Amazon SageMaker Endpoint。

## 前置条件

- AWS 账号及配置好的 CLI 凭证
- Docker
- Python 3.9+ 及 boto3, sagemaker SDK
- SageMaker 执行角色（如 `SageMakerExecutionRole`）
- ml.g6e.2xlarge endpoint 配额（需申请）

## 快速开始

```bash
# 1. 构建容器镜像并推送到 ECR
./0_build_and_push.sh

# 2. 下载模型（约 19GB）
python 1_download_model.py

# 3. 上传模型到 S3（未压缩方式，加速部署）
python 2_upload_model.py

# 4. 部署 Endpoint
python 3_deploy.py
```

## 配置

设置 AWS 区域（默认 us-east-2）：

```bash
export AWS_REGION=us-east-2
```

## 部署信息

| 项目 | 说明 |
|-----|------|
| 实例类型 | ml.g6e.2xlarge (L40S 48GB) |
| 模型大小 | ~19 GB |
| 部署时间 | ~7-8 分钟 |
| 基础镜像 | vllm/vllm-openai:v0.14.1 |

## 测试

```python
import boto3
import json

client = boto3.client('sagemaker-runtime', region_name='us-east-2')
response = client.invoke_endpoint(
    EndpointName='autoglm-phone-9b-XXXXXXXX-XXXXXX',  # 替换为实际名称
    ContentType='application/json',
    Body=json.dumps({
        "model": "autoglm-phone-9b",
        "messages": [{"role": "user", "content": "打开微信"}]
    })
)
print(json.loads(response['Body'].read()))
```

## 文件说明

| 文件 | 说明 |
|-----|------|
| `0_build_and_push.sh` | 构建并推送 Docker 镜像到 ECR |
| `1_download_model.py` | 从 HuggingFace 下载模型 |
| `2_upload_model.py` | 上传未压缩模型到 S3 |
| `3_deploy.py` | 部署 SageMaker Endpoint |
| `Dockerfile` | 容器定义 |
| `code/model.py` | FastAPI 推理服务 |

## 注意事项

- 模型仅生成操作指令，完整的 Phone Agent 需要配合 ADB 连接手机使用
- 参考 [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM) 了解完整用法

## License

MIT
