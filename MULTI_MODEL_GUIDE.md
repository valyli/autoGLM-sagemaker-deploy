# 多模型并行部署指南

## 🎯 新架构设计

### 目录结构

```
autoGLM-sagemaker-deploy/
├── models/                    # 所有模型文件
│   ├── autoglm/              # AutoGLM 模型
│   ├── llama-3.2-vision/     # Llama Vision 模型
│   └── qwen2.5-7b/           # Qwen 模型
├── configs/                   # 所有配置文件
│   ├── autoglm.json          # AutoGLM 配置
│   ├── autoglm.env           # AutoGLM 环境变量
│   ├── llama-3.2-vision.json # Llama 配置
│   └── qwen2.5-7b.json       # Qwen 配置
├── deploy_multi.sh           # 多模型部署脚本
└── model_presets.ini         # 模型预设库
```

## 🚀 使用方法

### 1. 部署单个模型

```bash
./deploy_multi.sh autoglm
```

**输出**：
```
configs/autoglm.json          # 配置文件
models/autoglm/               # 模型文件
Endpoint: autoglm-phone-9b-xxx
```

### 2. 同时部署多个模型

```bash
./deploy_multi.sh autoglm llama-3.2-vision qwen2.5-7b
```

**自动完成**：
- ✅ 下载 3 个模型到不同目录
- ✅ 上传到不同 S3 路径
- ✅ 创建 3 个独立 Endpoint
- ✅ 保存 3 个配置文件

### 3. 查看已部署的模型

```bash
./deploy_multi.sh --list
```

**输出**：
```
已部署的模型
==========================================

📦 预设: autoglm
   模型: zai-org/AutoGLM-Phone-9B
   Endpoint: autoglm-phone-9b-20260213-144459
   区域: us-west-2

📦 预设: llama-3.2-vision
   模型: meta-llama/Llama-3.2-11B-Vision-Instruct
   Endpoint: llama-vision-20260213-150230
   区域: us-west-2

📦 预设: qwen2.5-7b
   模型: Qwen/Qwen2.5-7B-Instruct
   Endpoint: qwen2.5-20260213-152145
   区域: us-west-2
```

## 📊 对比：单模型 vs 多模型

### 旧方式（单模型）

```bash
# 部署 AutoGLM
./switch_model.sh autoglm
./install.sh

# 切换到 Llama（会覆盖 AutoGLM）
./switch_model.sh llama-3.2-vision
rm -rf model/ config.json
./install.sh

# ❌ AutoGLM 配置丢失
# ❌ 需要重新部署才能用回 AutoGLM
```

### 新方式（多模型）

```bash
# 同时部署两个模型
./deploy_multi.sh autoglm llama-3.2-vision

# ✅ 两个模型同时可用
# ✅ 配置独立保存
# ✅ 随时切换使用
```

## 🔧 工作原理

### 环境变量隔离

```bash
# AutoGLM 部署
MODEL_ID=zai-org/AutoGLM-Phone-9B
MODEL_DIR=models/autoglm
CONFIG_FILE=configs/autoglm.json

# Llama 部署
MODEL_ID=meta-llama/Llama-3.2-11B-Vision
MODEL_DIR=models/llama-3.2-vision
CONFIG_FILE=configs/llama-3.2-vision.json
```

### S3 路径隔离

```
s3://sagemaker-us-west-2-xxx/
├── models/
│   ├── autoglm-phone-9b/        # AutoGLM 模型
│   ├── llama-3.2-11b-vision/    # Llama 模型
│   └── qwen2.5-7b-instruct/     # Qwen 模型
```

### Endpoint 独立

```
autoglm-phone-9b-20260213-144459      # AutoGLM Endpoint
llama-vision-20260213-150230          # Llama Endpoint
qwen2.5-20260213-152145               # Qwen Endpoint
```

## 💡 使用场景

### 场景 1: A/B 测试

```bash
# 部署两个版本对比
./deploy_multi.sh autoglm autoglm-multilingual

# 测试 AutoGLM
python3 test_endpoint.py --config configs/autoglm.json

# 测试多语言版本
python3 test_endpoint.py --config configs/autoglm-multilingual.json
```

### 场景 2: 多任务支持

```bash
# 部署不同用途的模型
./deploy_multi.sh autoglm qwen2.5-7b

# 手机操作任务 → AutoGLM
# 文本对话任务 → Qwen
```

### 场景 3: 开发/生产环境

```bash
# 开发环境：小模型
./deploy_multi.sh llama-3.2-text

# 生产环境：大模型
./deploy_multi.sh llama-3.2-vision
```

## 📝 配置文件示例

### configs/autoglm.json

```json
{
  "model_data_url": "s3://sagemaker-us-west-2-xxx/models/autoglm-phone-9b/",
  "compression": "None",
  "region": "us-west-2",
  "endpoint_name": "autoglm-phone-9b-20260213-144459",
  "preset": "autoglm",
  "model_id": "zai-org/AutoGLM-Phone-9B"
}
```

### configs/autoglm.env

```bash
MODEL_ID=zai-org/AutoGLM-Phone-9B
SERVED_MODEL_NAME=autoglm-phone-9b
MAX_MODEL_LEN=25480
DTYPE=bfloat16
MODEL_TYPE=multimodal
INSTANCE_TYPE=ml.g6e.xlarge
AWS_REGION=us-west-2
MODEL_DIR=models/autoglm
CONFIG_FILE=configs/autoglm.json
```

## 🎨 测试多个 Endpoint

### 创建测试脚本

```python
# test_multi.py
import boto3
import json
import sys

def test_endpoint(config_file, prompt):
    with open(config_file) as f:
        config = json.load(f)
    
    endpoint = config['endpoint_name']
    region = config['region']
    preset = config['preset']
    
    print(f"测试 {preset}: {endpoint}")
    
    client = boto3.client('sagemaker-runtime', region_name=region)
    response = client.invoke_endpoint(
        EndpointName=endpoint,
        ContentType='application/json',
        Body=json.dumps({
            "model": config.get('served_model_name', 'model'),
            "messages": [{"role": "user", "content": prompt}]
        })
    )
    
    result = json.loads(response['Body'].read())
    print(f"回复: {result['choices'][0]['message']['content']}\n")

# 测试所有模型
test_endpoint('configs/autoglm.json', '打开微信')
test_endpoint('configs/llama-3.2-vision.json', 'Describe this image')
test_endpoint('configs/qwen2.5-7b.json', '你好')
```

## 🗑️ 删除 Endpoint

### 使用删除脚本（推荐）

```bash
# 1. 查看已部署的 endpoint
./delete_endpoint.sh --list

# 2. 通过预设名删除
./delete_endpoint.sh autoglm

# 3. 通过 endpoint 名称删除
./delete_endpoint.sh autoglm-phone-9b-20260219-032628

# 4. 删除所有
./delete_endpoint.sh --all
```

### 删除内容

脚本会自动删除：
- ✅ SageMaker Endpoint
- ✅ Endpoint Configuration
- ✅ Model
- ✅ 本地配置文件 (`configs/*.json`)

### 删除示例

```bash
$ ./delete_endpoint.sh autoglm

[WARN] 准备删除 Endpoint: autoglm-phone-9b-20260219-032628
区域: us-west-2

确认删除? (yes/no): yes

[INFO] 删除 Endpoint...
[INFO] ✓ Endpoint 已删除
[INFO] 删除 Endpoint Config...
[INFO] ✓ Endpoint Config 已删除
[INFO] 删除 Model...
[INFO] ✓ Model 已删除
[INFO] 删除本地配置...
[INFO] ✓ 配置文件已删除

[INFO] ==========================================
[INFO] ✅ 删除完成
[INFO] ==========================================
```

### 手动删除（不推荐）

```bash
# 停止单个
aws sagemaker delete-endpoint \
  --endpoint-name autoglm-phone-9b-xxx \
  --region us-west-2

# 批量停止
for config in configs/*.json; do
  endpoint=$(jq -r '.endpoint_name' "$config")
  aws sagemaker delete-endpoint --endpoint-name "$endpoint" --region us-west-2
done
```

## 💰 成本管理

### 查看运行成本

```bash
# 列出所有 Endpoint
aws sagemaker list-endpoints --region us-west-2

# 或使用脚本
./delete_endpoint.sh --list

# 计算总成本
# ml.g6e.xlarge: $0.503/小时 × 3 = $1.509/小时
```

### 💡 成本优化建议

1. **及时删除不用的 Endpoint**
   ```bash
   ./delete_endpoint.sh autoglm  # 立即停止计费
   ```

2. **使用较小实例**
   - ml.g6e.xlarge ($0.503/h) vs ml.g6e.2xlarge ($1.006/h)
   - 编辑 `model_presets.ini` 修改 `INSTANCE_TYPE`

3. **按需部署**
   - 不要同时运行所有模型
   - 用完立即删除

4. **定期检查**
   ```bash
   # 每周检查一次
   ./delete_endpoint.sh --list
   ```

## 🔄 迁移指南

### 从单模型迁移到多模型

```bash
# 1. 备份现有配置
cp config.json configs/autoglm.json
cp -r model models/autoglm

# 2. 使用新脚本部署其他模型
./deploy_multi.sh llama-3.2-vision qwen2.5-7b

# 3. 清理旧文件
rm config.json
rm -rf model/
```

## 📚 总结

### 优势

| 特性 | 单模型 | 多模型 |
|------|--------|--------|
| **同时运行** | ❌ 只能一个 | ✅ 无限制 |
| **配置管理** | ❌ 会覆盖 | ✅ 独立保存 |
| **切换成本** | ❌ 需重新部署 | ✅ 即时切换 |
| **A/B 测试** | ❌ 不支持 | ✅ 完美支持 |
| **目录结构** | ❌ 混乱 | ✅ 清晰 |

### 核心命令

```bash
# 部署
./deploy_multi.sh <preset1> [preset2] ...

# 查看
./deploy_multi.sh --list

# 测试
python3 test_endpoint.py --config configs/<preset>.json

# 删除
./delete_endpoint.sh <preset>           # 删除单个
./delete_endpoint.sh --all              # 删除所有
./delete_endpoint.sh --list             # 查看所有
```

**现在你可以同时运行多个模型，随时切换使用！** 🎉
