#!/usr/bin/env python3
"""上传未压缩模型到 S3（跳过打包，加速部署）"""
import os
import json
import boto3
import warnings
from concurrent.futures import ThreadPoolExecutor

warnings.filterwarnings('ignore', category=DeprecationWarning)

def load_config():
    config = {'AWS_REGION': 'us-west-2'}
    if os.path.exists('deploy.config'):
        with open('deploy.config') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    return os.environ.get('AWS_REGION', config['AWS_REGION'])

REGION = load_config()
LOCAL_MODEL_DIR = "model"
S3_PREFIX = "models/autoglm-phone-9b-uncompressed"

uploaded_count = 0
total_files = 0

def upload_file(args):
    global uploaded_count
    s3_client, bucket, local_path, s3_key = args
    try:
        s3_client.upload_file(local_path, bucket, s3_key)
        uploaded_count += 1
        if uploaded_count % 10 == 0:
            print(f"  已上传: {uploaded_count}/{total_files}")
        return s3_key
    except Exception as e:
        print(f"\n❌ 上传失败: {local_path}\n错误: {e}")
        raise

def main():
    if not os.path.exists(LOCAL_MODEL_DIR) or not os.listdir(LOCAL_MODEL_DIR):
        print("❌ 请先运行: python 1_download_model.py")
        return
    
    sts = boto3.client('sts', region_name=REGION)
    account_id = sts.get_caller_identity()['Account']
    bucket = f"sagemaker-{REGION}-{account_id}"
    s3_client = boto3.client('s3', region_name=REGION)
    
    # 创建 bucket（如果不存在）
    try:
        s3_client.head_bucket(Bucket=bucket)
        print(f"✓ S3 bucket 已存在: {bucket}")
    except:
        print(f"创建 S3 bucket: {bucket}")
        try:
            if REGION == 'us-east-1':
                s3_client.create_bucket(Bucket=bucket)
            else:
                s3_client.create_bucket(
                    Bucket=bucket,
                    CreateBucketConfiguration={'LocationConstraint': REGION}
                )
            print(f"✓ Bucket 创建成功")
        except Exception as e:
            print(f"❌ 创建 bucket 失败: {e}")
            raise
    
    # 收集所有文件
    files = []
    for root, _, filenames in os.walk(LOCAL_MODEL_DIR):
        for f in filenames:
            local_path = os.path.join(root, f)
            rel_path = os.path.relpath(local_path, LOCAL_MODEL_DIR)
            s3_key = f"{S3_PREFIX}/{rel_path}"
            files.append((s3_client, bucket, local_path, s3_key))
    
    global total_files
    total_files = len(files)
    print(f"⏳ 上传 {total_files} 个文件到 s3://{bucket}/{S3_PREFIX}/")
    
    # 并行上传
    try:
        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(upload_file, files))
    except Exception as e:
        print(f"\n❌ 上传中断")
        raise
    
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
