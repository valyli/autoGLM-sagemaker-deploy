#!/bin/bash
set -e

echo "=========================================="
echo "AutoGLM-Phone-9B SageMaker 自动部署"
echo "=========================================="

# 检查前置条件
check_prerequisites() {
    echo -e "\n[1/5] 检查前置条件..."
    
    if ! command -v aws &> /dev/null; then
        echo "❌ AWS CLI 未安装"
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker 未安装"
        exit 1
    fi
    
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python3 未安装"
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        echo "❌ AWS 凭证未配置"
        exit 1
    fi
    
    echo "✓ 前置条件检查通过"
}

# 安装 Python 依赖
install_dependencies() {
    echo -e "\n[2/5] 安装 Python 依赖..."
    
    if [ ! -f "requirements.txt" ]; then
        cat > requirements.txt << 'EOF'
boto3
sagemaker>=2.0
huggingface_hub
EOF
    fi
    
    pip3 install -q --upgrade -r requirements.txt
    echo "✓ 依赖安装完成"
}

# 创建 SageMaker 执行角色
create_role() {
    echo -e "\n[3/5] 检查 SageMaker 执行角色..."
    
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    ROLE_NAME="SageMakerExecutionRole"
    
    if aws iam get-role --role-name $ROLE_NAME &> /dev/null; then
        echo "✓ 角色已存在: $ROLE_NAME"
        return
    fi
    
    echo "创建角色: $ROLE_NAME"
    
    cat > /tmp/trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "sagemaker.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF
    
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        --output text > /dev/null
    
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
    
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
    
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
    
    rm /tmp/trust-policy.json
    
    echo "✓ 角色创建完成，等待生效..."
    sleep 10
}

# 构建并推送 Docker 镜像
build_and_push() {
    echo -e "\n[4/5] 构建并推送 Docker 镜像..."
    
    if [ -f "./0_build_and_push.sh" ]; then
        chmod +x ./0_build_and_push.sh
        ./0_build_and_push.sh
    else
        echo "❌ 0_build_and_push.sh 不存在"
        exit 1
    fi
    
    echo "✓ 镜像推送完成"
}

# 下载模型
download_model() {
    echo -e "\n[5/5] 下载模型 (~19GB)..."
    
    if [ -d "model" ] && [ "$(ls -A model)" ]; then
        echo "✓ 模型已存在，跳过下载"
        return
    fi
    
    python3 1_download_model.py
    echo "✓ 模型下载完成"
}

# 上传模型到 S3
upload_model() {
    echo -e "\n[6/7] 上传模型到 S3..."
    
    if [ -f "config.json" ]; then
        echo "✓ 模型已上传，跳过"
        return
    fi
    
    python3 2_upload_model.py 2>&1 | grep -v "PythonDeprecationWarning" || true
    echo "✓ 模型上传完成"
}

# 部署 Endpoint
deploy_endpoint() {
    echo -e "\n[7/7] 部署 SageMaker Endpoint..."
    echo "⏳ 预计需要 15 分钟..."
    
    python3 3_deploy.py
}

# 主流程
main() {
    check_prerequisites
    install_dependencies
    create_role
    build_and_push
    download_model
    upload_model
    deploy_endpoint
    
    echo -e "\n=========================================="
    echo "✅ 部署完成！"
    echo "=========================================="
    
    if [ -f "config.json" ]; then
        echo -e "\n查看 config.json 获取 Endpoint 信息"
    fi
}

# 错误处理
trap 'echo -e "\n❌ 部署失败，请检查错误信息"; exit 1' ERR

main
