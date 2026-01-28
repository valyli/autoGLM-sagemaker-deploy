#!/usr/bin/env python3
"""Deploy AutoGLM-Phone-9B to SageMaker Endpoint"""

import json
import os
import boto3
import sagemaker
from sagemaker.model import Model
from datetime import datetime

REGION = os.environ.get("AWS_REGION", "us-east-2")
INSTANCE_TYPE = "ml.g6e.2xlarge"

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
    endpoint_name = f"autoglm-phone-9b-{timestamp}"
    
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    image_uri = f"{account_id}.dkr.ecr.{REGION}.amazonaws.com/autoglm-vllm-byoc:latest"
    
    print(f"Endpoint: {endpoint_name}")
    print(f"Model: {config['model_data_url']}")
    print(f"Image: {image_uri}")
    
    model = Model(
        name=f"autoglm-phone-9b-model-{timestamp}",
        image_uri=image_uri,
        model_data={
            "S3DataSource": {
                "S3Uri": config["model_data_url"],
                "S3DataType": "S3Prefix",
                "CompressionType": "None"
            }
        },
        role=get_execution_role(),
        sagemaker_session=sagemaker.Session(boto_session=boto3.Session(region_name=REGION)),
        env={"VLLM_WORKER_MULTIPROC_METHOD": "spawn"}
    )
    
    print(f"\n部署中，预计 15 分钟...")
    model.deploy(
        initial_instance_count=1,
        instance_type=INSTANCE_TYPE,
        endpoint_name=endpoint_name,
        container_startup_health_check_timeout=1800,
        wait=True
    )
    print(f"\n✅ 部署成功: {endpoint_name}")

if __name__ == "__main__":
    main()
