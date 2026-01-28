#!/usr/bin/env python3
"""上传未压缩模型到 S3（跳过打包，加速部署）"""
import os
import json
import boto3
from concurrent.futures import ThreadPoolExecutor

REGION = os.environ.get("AWS_REGION", "us-east-2")
LOCAL_MODEL_DIR = "model"
S3_PREFIX = "models/autoglm-phone-9b-uncompressed"

def upload_file(args):
    s3_client, bucket, local_path, s3_key = args
    s3_client.upload_file(local_path, bucket, s3_key)
    return s3_key

def main():
    if not os.path.exists(LOCAL_MODEL_DIR) or not os.listdir(LOCAL_MODEL_DIR):
        print("❌ 请先运行: python 1_download_model.py")
        return
    
    sts = boto3.client('sts', region_name=REGION)
    account_id = sts.get_caller_identity()['Account']
    bucket = f"sagemaker-{REGION}-{account_id}"
    s3_client = boto3.client('s3', region_name=REGION)
    
    # 收集所有文件
    files = []
    for root, _, filenames in os.walk(LOCAL_MODEL_DIR):
        for f in filenames:
            local_path = os.path.join(root, f)
            rel_path = os.path.relpath(local_path, LOCAL_MODEL_DIR)
            s3_key = f"{S3_PREFIX}/{rel_path}"
            files.append((s3_client, bucket, local_path, s3_key))
    
    print(f"⏳ 上传 {len(files)} 个文件到 s3://{bucket}/{S3_PREFIX}/")
    
    # 并行上传
    with ThreadPoolExecutor(max_workers=10) as executor:
        list(executor.map(upload_file, files))
    
    model_data_url = f"s3://{bucket}/{S3_PREFIX}/"
    
    config = {
        "model_data_url": model_data_url,
        "compression": "None",
        "region": REGION
    }
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✅ 完成: {model_data_url}")

if __name__ == "__main__":
    main()
