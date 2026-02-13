# AutoGLM-Phone-9B SageMaker 部署

将 [AutoGLM-Phone-9B](https://huggingface.co/zai-org/AutoGLM-Phone-9B) 视觉语言模型部署到 Amazon SageMaker Endpoint。

## 前置条件

- AWS 账号及配置好的 CLI 凭证
- Docker
- Python 3.10+ 及依赖（`pip install -r requirements.txt`）
- SageMaker 执行角色（见下方创建说明）
- ml.g6e.2xlarge endpoint 配额（需申请）

### 创建 SageMaker 执行角色

如果没有 SageMaker 执行角色，运行以下命令创建：

```bash
# 创建信任策略文件
cat > trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "sagemaker.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# 创建角色
aws iam create-role \
  --role-name SageMakerExecutionRole \
  --assume-role-policy-document file://trust-policy.json

# 附加必要策略
aws iam attach-role-policy \
  --role-name SageMakerExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess

aws iam attach-role-policy \
  --role-name SageMakerExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

aws iam attach-role-policy \
  --role-name SageMakerExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

# 清理临时文件
rm trust-policy.json
```

## 快速开始

### 方式一：一键自动部署（推荐）

```bash
./install.sh
```

### 方式二：手动分步部署

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

编辑 `deploy.config` 文件自定义部署参数：

```bash
# 模型选择
MODEL_ID=zai-org/AutoGLM-Phone-9B  # 或 AutoGLM-Phone-9B-Multilingual

# AWS 区域
AWS_REGION=us-west-2

# 实例类型（根据配额选择）
INSTANCE_TYPE=ml.g6e.2xlarge  # 或 ml.g6e.xlarge, ml.g5.2xlarge
```

或使用环境变量：

```bash
export MODEL_ID=zai-org/AutoGLM-Phone-9B-Multilingual
export INSTANCE_TYPE=ml.g6e.xlarge
./install.sh
```

### 实例类型对比

| 实例类型 | GPU | 显存 | 成本/小时 | 适用场景 |
|---------|-----|------|----------|----------|
| ml.g6e.xlarge | L40S | 24GB | $0.503 | 最小配置 |
| ml.g6e.2xlarge | L40S | 48GB | $1.006 | 推荐 |
| ml.g5.xlarge | A10G | 24GB | $1.006 | 备选 |
| ml.g5.2xlarge | A10G | 24GB | $1.515 | 高性能 |

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

client = boto3.client('sagemaker-runtime', region_name='us-west-2')
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
| `deploy.config` | 部署配置文件（模型/实例选择） |
| `install.sh` | 一键自动部署脚本 |
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
