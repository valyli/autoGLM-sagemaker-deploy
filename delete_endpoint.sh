#!/bin/bash
# 删除 SageMaker Endpoint
# 用法: ./delete_endpoint.sh [preset|endpoint-name|--all]

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 显示用法
show_usage() {
    echo "=========================================="
    echo "删除 SageMaker Endpoint"
    echo "=========================================="
    echo ""
    echo "用法:"
    echo "  ./delete_endpoint.sh <preset>           # 通过预设名删除"
    echo "  ./delete_endpoint.sh <endpoint-name>    # 通过 endpoint 名删除"
    echo "  ./delete_endpoint.sh --all              # 删除所有已部署的"
    echo "  ./delete_endpoint.sh --list             # 列出所有 endpoint"
    echo ""
    echo "示例:"
    echo "  ./delete_endpoint.sh autoglm"
    echo "  ./delete_endpoint.sh autoglm-phone-9b-20260219-032628"
    echo "  ./delete_endpoint.sh --all"
    echo ""
}

# 列出所有 endpoint
list_endpoints() {
    echo "=========================================="
    echo "已部署的 Endpoint"
    echo "=========================================="
    
    REGION=${AWS_REGION:-us-west-2}
    
    # 从配置文件读取
    if [ -d "configs" ]; then
        for config in configs/*.json; do
            if [ -f "$config" ]; then
                preset=$(basename "$config" .json)
                endpoint=$(jq -r '.endpoint_name // "N/A"' "$config")
                model=$(jq -r '.model_id // "N/A"' "$config")
                
                echo ""
                echo "📦 预设: $preset"
                echo "   模型: $model"
                echo "   Endpoint: $endpoint"
                echo "   配置: $config"
            fi
        done
    fi
    
    # 从 AWS 读取所有 endpoint
    echo ""
    echo "=========================================="
    echo "AWS 中的所有 Endpoint"
    echo "=========================================="
    aws sagemaker list-endpoints --region $REGION --output table
}

# 删除单个 endpoint
delete_endpoint() {
    local target=$1
    local endpoint_name=""
    local config_file=""
    
    REGION=${AWS_REGION:-us-west-2}
    
    # 检查是否是预设名
    if [ -f "configs/${target}.json" ]; then
        config_file="configs/${target}.json"
        endpoint_name=$(jq -r '.endpoint_name' "$config_file")
        log_info "从配置文件读取: $config_file"
    else
        # 假设是 endpoint 名称
        endpoint_name=$target
    fi
    
    log_warn "准备删除 Endpoint: $endpoint_name"
    echo "区域: $REGION"
    echo ""
    
    read -p "确认删除? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_info "取消删除"
        return 0
    fi
    
    # 删除 endpoint
    log_info "删除 Endpoint..."
    if aws sagemaker delete-endpoint \
        --endpoint-name "$endpoint_name" \
        --region $REGION 2>/dev/null; then
        log_info "✓ Endpoint 已删除: $endpoint_name"
    else
        log_error "删除 Endpoint 失败（可能已不存在）"
    fi
    
    # 删除 endpoint config
    log_info "删除 Endpoint Config..."
    endpoint_config=$(aws sagemaker describe-endpoint \
        --endpoint-name "$endpoint_name" \
        --region $REGION \
        --query 'EndpointConfigName' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$endpoint_config" ] && [ "$endpoint_config" != "None" ]; then
        aws sagemaker delete-endpoint-config \
            --endpoint-config-name "$endpoint_config" \
            --region $REGION 2>/dev/null || true
        log_info "✓ Endpoint Config 已删除: $endpoint_config"
    fi
    
    # 删除 model
    log_info "删除 Model..."
    model_name=$(aws sagemaker describe-endpoint-config \
        --endpoint-config-name "$endpoint_config" \
        --region $REGION \
        --query 'ProductionVariants[0].ModelName' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$model_name" ] && [ "$model_name" != "None" ]; then
        aws sagemaker delete-model \
            --model-name "$model_name" \
            --region $REGION 2>/dev/null || true
        log_info "✓ Model 已删除: $model_name"
    fi
    
    # 删除本地配置文件
    if [ -n "$config_file" ] && [ -f "$config_file" ]; then
        log_info "删除本地配置..."
        rm -f "$config_file"
        rm -f "configs/${target}.env"
        log_info "✓ 配置文件已删除"
    fi
    
    echo ""
    log_info "=========================================="
    log_info "✅ 删除完成: $endpoint_name"
    log_info "=========================================="
}

# 删除所有 endpoint
delete_all() {
    log_warn "准备删除所有已部署的 Endpoint"
    echo ""
    
    if [ ! -d "configs" ] || [ -z "$(ls -A configs/*.json 2>/dev/null)" ]; then
        log_warn "没有找到已部署的 Endpoint"
        return 0
    fi
    
    # 列出所有
    for config in configs/*.json; do
        if [ -f "$config" ]; then
            preset=$(basename "$config" .json)
            endpoint=$(jq -r '.endpoint_name' "$config")
            echo "  - $preset: $endpoint"
        fi
    done
    
    echo ""
    read -p "确认删除所有? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_info "取消删除"
        return 0
    fi
    
    # 删除所有
    for config in configs/*.json; do
        if [ -f "$config" ]; then
            preset=$(basename "$config" .json)
            echo ""
            log_info "删除: $preset"
            delete_endpoint "$preset"
        fi
    done
}

# 主函数
main() {
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi
    
    case "$1" in
        --list|-l)
            list_endpoints
            ;;
        --all|-a)
            delete_all
            ;;
        --help|-h)
            show_usage
            ;;
        *)
            delete_endpoint "$1"
            ;;
    esac
}

main "$@"
