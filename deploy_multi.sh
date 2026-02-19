#!/bin/bash
# 多模型并行部署脚本
# 用法: ./deploy_multi.sh <preset1> <preset2> ...
# 示例: ./deploy_multi.sh autoglm llama-3.2-vision qwen2.5-7b

set -e

PRESETS_FILE="model_presets.ini"
CONFIGS_DIR="configs"
MODELS_DIR="models"

# 创建必要目录
mkdir -p $CONFIGS_DIR $MODELS_DIR

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# 显示用法
show_usage() {
    echo "=========================================="
    echo "多模型并行部署工具"
    echo "=========================================="
    echo ""
    echo "用法:"
    echo "  ./deploy_multi.sh <preset1> [preset2] [preset3] ..."
    echo ""
    echo "可用预设:"
    grep "^\[" $PRESETS_FILE | tr -d '[]' | sed 's/^/  - /'
    echo ""
    echo "示例:"
    echo "  # 部署单个模型"
    echo "  ./deploy_multi.sh autoglm"
    echo ""
    echo "  # 同时部署多个模型"
    echo "  ./deploy_multi.sh autoglm llama-3.2-vision qwen2.5-7b"
    echo ""
    echo "  # 查看已部署的模型"
    echo "  ./deploy_multi.sh --list"
    echo ""
}

# 列出已部署的模型
list_deployed() {
    echo "=========================================="
    echo "已部署的模型"
    echo "=========================================="
    
    if [ ! -d "$CONFIGS_DIR" ] || [ -z "$(ls -A $CONFIGS_DIR 2>/dev/null)" ]; then
        log_warn "暂无已部署的模型"
        return
    fi
    
    for config_file in $CONFIGS_DIR/*.json; do
        if [ -f "$config_file" ]; then
            preset=$(basename "$config_file" .json)
            endpoint=$(jq -r '.endpoint_name // "N/A"' "$config_file")
            model_id=$(jq -r '.model_id // "N/A"' "$config_file")
            region=$(jq -r '.region // "N/A"' "$config_file")
            
            echo ""
            echo "📦 预设: $preset"
            echo "   模型: $model_id"
            echo "   Endpoint: $endpoint"
            echo "   区域: $region"
        fi
    done
    echo ""
}

# 加载预设配置
load_preset() {
    local preset=$1
    local config_file="$CONFIGS_DIR/${preset}.env"
    
    if ! grep -q "^\[$preset\]" $PRESETS_FILE; then
        log_error "预设 '$preset' 不存在"
        return 1
    fi
    
    log_info "加载预设: $preset"
    
    # 转义特殊字符用于正则表达式
    local escaped_preset=$(echo "$preset" | sed 's/\./\\./g')
    
    # 提取预设配置（使用空行作为分隔符）
    awk "/^\[$escaped_preset\]/,/^$/ {if (/=/) print}" $PRESETS_FILE > "$config_file"
    
    # 添加模型特定的目录
    echo "MODEL_DIR=$MODELS_DIR/$preset" >> "$config_file"
    echo "CONFIG_FILE=$CONFIGS_DIR/${preset}.json" >> "$config_file"
    
    log_success "配置已加载: $config_file"
    return 0
}

# 部署单个模型
deploy_model() {
    local preset=$1
    local config_file="$CONFIGS_DIR/${preset}.env"
    
    log_info "=========================================="
    log_info "开始部署: $preset"
    log_info "=========================================="
    
    # 加载配置
    if [ ! -f "$config_file" ]; then
        log_error "配置文件不存在: $config_file"
        return 1
    fi
    
    # 导出环境变量
    set -a
    source "$config_file"
    set +a
    
    # 写入 deploy_vars.json
    cat > deploy_vars.json << EOF
{
  "MODEL_ID": "$MODEL_ID",
  "AWS_REGION": "${AWS_REGION:-us-west-2}",
  "INSTANCE_TYPE": "$INSTANCE_TYPE",
  "SERVED_MODEL_NAME": "${SERVED_MODEL_NAME:-model}",
  "MAX_MODEL_LEN": "${MAX_MODEL_LEN:-4096}",
  "DTYPE": "${DTYPE:-auto}",
  "MODEL_TYPE": "${MODEL_TYPE:-text}"
}
EOF
    
    log_info "模型ID: $MODEL_ID"
    log_info "区域: ${AWS_REGION:-us-west-2}"
    log_info "实例类型: $INSTANCE_TYPE"
    log_info "模型目录: $MODEL_DIR"
    
    # 1. 下载模型
    if [ -d "$MODEL_DIR" ] && [ "$(ls -A $MODEL_DIR)" ]; then
        log_warn "模型已存在，跳过下载: $MODEL_DIR"
    else
        log_info "[1/3] 下载模型..."
        mkdir -p "$MODEL_DIR"
        
        # 临时修改 1_download_model.py 的输出目录
        LOCAL_DIR="$MODEL_DIR" python3 1_download_model.py
        
        if [ $? -ne 0 ]; then
            log_error "模型下载失败"
            return 1
        fi
        log_success "模型下载完成"
    fi
    
    # 2. 上传到 S3
    log_info "[2/3] 上传模型到 S3..."
    LOCAL_MODEL_DIR="$MODEL_DIR" python3 2_upload_model.py
    
    if [ $? -ne 0 ]; then
        log_error "模型上传失败"
        return 1
    fi
    
    # 移动 config.json 到 configs 目录
    if [ -f "config.json" ]; then
        mv config.json "$CONFIG_FILE"
        # 添加模型信息
        jq ". + {\"preset\": \"$preset\", \"model_id\": \"$MODEL_ID\"}" "$CONFIG_FILE" > "$CONFIG_FILE.tmp"
        mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
        log_success "配置已保存: $CONFIG_FILE"
    fi
    
    # 2.5. 构建并推送 Docker 镜像（如果不存在）
    log_info "[2.5/3] 检查 Docker 镜像..."
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    IMAGE_URI="$ACCOUNT_ID.dkr.ecr.${AWS_REGION:-us-west-2}.amazonaws.com/autoglm-vllm-byoc:latest"
    
    # 检查镜像是否存在
    if aws ecr describe-images --repository-name autoglm-vllm-byoc --image-ids imageTag=latest --region ${AWS_REGION:-us-west-2} &>/dev/null; then
        log_success "镜像已存在: $IMAGE_URI"
    else
        log_warn "镜像不存在，开始构建..."
        AWS_REGION=${AWS_REGION:-us-west-2} ./0_build_and_push.sh
        if [ $? -ne 0 ]; then
            log_error "镜像构建失败"
            return 1
        fi
        log_success "镜像构建完成"
    fi
    
    # 3. 部署 Endpoint
    log_info "[3/3] 部署 SageMaker Endpoint..."
    CONFIG_JSON="$CONFIG_FILE" python3 3_deploy.py
    
    if [ $? -ne 0 ]; then
        log_error "Endpoint 部署失败"
        return 1
    fi
    
    log_success "=========================================="
    log_success "✅ $preset 部署完成！"
    log_success "=========================================="
    
    # 显示部署信息
    if [ -f "$CONFIG_FILE" ]; then
        endpoint=$(jq -r '.endpoint_name' "$CONFIG_FILE")
        echo ""
        echo "Endpoint: $endpoint"
        echo "配置文件: $CONFIG_FILE"
        echo ""
        echo "测试命令:"
        echo "  python3 test_endpoint.py --config $CONFIG_FILE"
    fi
    
    return 0
}

# 主函数
main() {
    # 检查参数
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi
    
    # 特殊命令
    if [ "$1" == "--list" ] || [ "$1" == "-l" ]; then
        list_deployed
        exit 0
    fi
    
    if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
        show_usage
        exit 0
    fi
    
    # 检查前置条件
    log_info "检查前置条件..."
    
    if ! command -v jq &> /dev/null; then
        log_error "需要安装 jq: sudo yum install -y jq"
        exit 1
    fi
    
    if ! command -v aws &> /dev/null; then
        log_error "需要安装 AWS CLI"
        exit 1
    fi
    
    log_success "前置条件检查通过"
    
    # 记录开始时间
    START_TIME=$(date +%s)
    
    # 加载所有预设配置
    log_info "=========================================="
    log_info "准备部署 $# 个模型"
    log_info "=========================================="
    
    for preset in "$@"; do
        load_preset "$preset" || exit 1
    done
    
    echo ""
    log_info "配置加载完成，开始部署..."
    echo ""
    
    # 部署所有模型
    SUCCESS_COUNT=0
    FAIL_COUNT=0
    
    for preset in "$@"; do
        if deploy_model "$preset"; then
            ((SUCCESS_COUNT++))
        else
            ((FAIL_COUNT++))
            log_error "$preset 部署失败，继续下一个..."
        fi
        echo ""
    done
    
    # 计算耗时
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    MINUTES=$((DURATION / 60))
    SECONDS=$((DURATION % 60))
    
    # 显示总结
    echo "=========================================="
    echo "部署总结"
    echo "=========================================="
    echo "成功: $SUCCESS_COUNT"
    echo "失败: $FAIL_COUNT"
    echo "耗时: ${MINUTES}分${SECONDS}秒"
    echo ""
    
    if [ $SUCCESS_COUNT -gt 0 ]; then
        log_success "部署完成！查看已部署模型:"
        echo "  ./deploy_multi.sh --list"
    fi
    
    if [ $FAIL_COUNT -gt 0 ]; then
        exit 1
    fi
}

main "$@"
