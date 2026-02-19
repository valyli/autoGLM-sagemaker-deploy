#!/usr/bin/env python3
"""Deploy AutoGLM-Phone-9B to SageMaker Endpoint"""

import json
import os
import boto3
from datetime import datetime

def load_config():
    config_file = 'deploy_vars.json'
    if os.path.exists(config_file):
        with open(config_file) as f:
            return json.load(f)
    return {
        'AWS_REGION': 'us-west-2',
        'INSTANCE_TYPE': 'ml.g6e.2xlarge',
        'SERVED_MODEL_NAME': 'model',
        'MAX_MODEL_LEN': '4096',
        'DTYPE': 'auto',
        'MODEL_TYPE': 'text'
    }

config = load_config()
REGION = config['AWS_REGION']
INSTANCE_TYPE = config['INSTANCE_TYPE']
SERVED_MODEL_NAME = config['SERVED_MODEL_NAME']
MAX_MODEL_LEN = config['MAX_MODEL_LEN']
DTYPE = config['DTYPE']
MODEL_TYPE = config['MODEL_TYPE']

def get_execution_role():
    iam = boto3.client("iam")
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    for role_name in ["SageMakerExecutionRole", "AmazonSageMaker-ExecutionRole-20251220T140433"]:
        try:
            iam.get_role(RoleName=role_name)
            return f"arn:aws:iam::{account_id}:role/{role_name}"
        except iam.exceptions.NoSuchEntityException:
            continue
    raise RuntimeError("未找到 SageMaker 执行角色")

def main():
    # 从 deploy_vars.json 读取部署配置
    if not os.path.exists('deploy_vars.json'):
        print(f"❌ 配置文件不存在: deploy_vars.json")
        return
    
    # 从 CONFIG_JSON 环境变量读取 S3 配置文件路径
    config_file = os.environ.get('CONFIG_JSON', 'config.json')
    if not os.path.exists(config_file):
        print(f"❌ S3 配置文件不存在: {config_file}")
        return
    
    with open(config_file) as f:
        s3_config = json.load(f)
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    model_name = f"autoglm-phone-9b-model-{timestamp}"
    endpoint_config_name = f"autoglm-phone-9b-config-{timestamp}"
    endpoint_name = f"autoglm-phone-9b-{timestamp}"
    
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    image_uri = f"{account_id}.dkr.ecr.{REGION}.amazonaws.com/autoglm-vllm-byoc:latest"
    role_arn = get_execution_role()
    
    print(f"Endpoint: {endpoint_name}")
    print(f"Model: {s3_config['model_data_url']}")
    print(f"Image: {image_uri}")
    print(f"Instance: {INSTANCE_TYPE}")
    
    sm_client = boto3.client('sagemaker', region_name=REGION)
    
    # 1. 创建模型
    print("\n[1/3] 创建模型...")
    sm_client.create_model(
        ModelName=model_name,
        PrimaryContainer={
            'Image': image_uri,
            'ModelDataSource': {
                'S3DataSource': {
                    'S3Uri': s3_config['model_data_url'],
                    'S3DataType': 'S3Prefix',
                    'CompressionType': 'None'
                }
            },
            'Environment': {
                'VLLM_WORKER_MULTIPROC_METHOD': 'spawn',
                'SERVED_MODEL_NAME': SERVED_MODEL_NAME,
                'MAX_MODEL_LEN': MAX_MODEL_LEN,
                'DTYPE': DTYPE,
                'MODEL_TYPE': MODEL_TYPE
            }
        },
        ExecutionRoleArn=role_arn
    )
    print(f"✓ 模型创建完成: {model_name}")
    
    # 2. 创建 Endpoint 配置
    print("\n[2/3] 创建 Endpoint 配置...")
    sm_client.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        ProductionVariants=[{
            'VariantName': 'AllTraffic',
            'ModelName': model_name,
            'InitialInstanceCount': 1,
            'InstanceType': INSTANCE_TYPE,
            'ContainerStartupHealthCheckTimeoutInSeconds': 1800
        }]
    )
    print(f"✓ Endpoint 配置创建完成: {endpoint_config_name}")
    
    # 3. 创建 Endpoint
    print(f"\n[3/3] 部署 Endpoint（预计 15 分钟）...")
    sm_client.create_endpoint(
        EndpointName=endpoint_name,
        EndpointConfigName=endpoint_config_name
    )
    
    # 保存 endpoint 信息（即使部署失败也保存）
    s3_config['endpoint_name'] = endpoint_name
    with open(config_file, "w") as f:
        json.dump(s3_config, f, indent=2)
    
    # 等待部署完成
    print("⏳ 等待部署...")
    try:
        waiter = sm_client.get_waiter('endpoint_in_service')
        waiter.wait(
            EndpointName=endpoint_name,
            WaiterConfig={'Delay': 30, 'MaxAttempts': 60}
        )
        
        print(f"\n\n===========================================")
        print(f"✅ 部署成功: {endpoint_name}")
        print(f"===========================================")
    except Exception as e:
        # 获取失败原因
        response = sm_client.describe_endpoint(EndpointName=endpoint_name)
        status = response['EndpointStatus']
        failure_reason = response.get('FailureReason', 'Unknown')
        
        print(f"\n\n===========================================")
        print(f"❌ 部署失败: {endpoint_name}")
        print(f"状态: {status}")
        print(f"原因: {failure_reason}")
        print(f"===========================================")
        print(f"\n查看日志:")
        print(f"aws sagemaker describe-endpoint --endpoint-name {endpoint_name} --region {REGION}")
        raise
    
    print(f"\n测试命令:")
    print(f"python3 -c \"import boto3, json; client=boto3.client('sagemaker-runtime', region_name='{REGION}'); ")
    print(f"response=client.invoke_endpoint(EndpointName='{endpoint_name}', ContentType='application/json', ")
    print(f"Body=json.dumps({{'model':'autoglm-phone-9b','messages':[{{'role':'user','content':'打开微信'}}]}})); ")
    print(f"print(json.loads(response['Body'].read()))\"")

if __name__ == "__main__":
    main()
