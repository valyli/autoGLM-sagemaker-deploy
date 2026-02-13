#!/usr/bin/env python3
"""Deploy AutoGLM-Phone-9B to SageMaker Endpoint"""

import json
import os
import boto3
from datetime import datetime

def load_config():
    config = {
        'AWS_REGION': 'us-west-2',
        'INSTANCE_TYPE': 'ml.g6e.2xlarge',
        'SERVED_MODEL_NAME': 'autoglm-phone-9b'
    }
    if os.path.exists('deploy.config'):
        with open('deploy.config') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    # 环境变量优先
    config['AWS_REGION'] = os.environ.get('AWS_REGION', config['AWS_REGION'])
    config['INSTANCE_TYPE'] = os.environ.get('INSTANCE_TYPE', config['INSTANCE_TYPE'])
    return config

config = load_config()
REGION = config['AWS_REGION']
INSTANCE_TYPE = config['INSTANCE_TYPE']
SERVED_MODEL_NAME = config['SERVED_MODEL_NAME']

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
    if not os.path.exists("config.json"):
        print("❌ 请先运行: python 1_download_model.py && python 2_upload_model.py")
        return
    
    with open("config.json") as f:
        config = json.load(f)
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    model_name = f"autoglm-phone-9b-model-{timestamp}"
    endpoint_config_name = f"autoglm-phone-9b-config-{timestamp}"
    endpoint_name = f"autoglm-phone-9b-{timestamp}"
    
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    image_uri = f"{account_id}.dkr.ecr.{REGION}.amazonaws.com/autoglm-vllm-byoc:latest"
    role_arn = get_execution_role()
    
    print(f"Endpoint: {endpoint_name}")
    print(f"Model: {config['model_data_url']}")
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
                    'S3Uri': config['model_data_url'],
                    'S3DataType': 'S3Prefix',
                    'CompressionType': 'None'
                }
            },
            'Environment': {
                'VLLM_WORKER_MULTIPROC_METHOD': 'spawn'
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
    
    # 等待部署完成
    print("⏳ 等待部署...")
    waiter = sm_client.get_waiter('endpoint_in_service')
    waiter.wait(
        EndpointName=endpoint_name,
        WaiterConfig={'Delay': 30, 'MaxAttempts': 60}
    )
    
    print(f"\n\n===========================================")
    print(f"✅ 部署成功: {endpoint_name}")
    print(f"===========================================")
    
    # 保存 endpoint 信息
    config['endpoint_name'] = endpoint_name
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"\n测试命令:")
    print(f"python3 -c \"import boto3, json; client=boto3.client('sagemaker-runtime', region_name='{REGION}'); ")
    print(f"response=client.invoke_endpoint(EndpointName='{endpoint_name}', ContentType='application/json', ")
    print(f"Body=json.dumps({{'model':'autoglm-phone-9b','messages':[{{'role':'user','content':'打开微信'}}]}})); ")
    print(f"print(json.loads(response['Body'].read()))\"")

if __name__ == "__main__":
    main()
