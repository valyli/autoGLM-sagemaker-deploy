#!/usr/bin/env python3
"""下载 AutoGLM-Phone-9B 模型到本地"""
import os
import json
from huggingface_hub import snapshot_download
from datetime import datetime

# 从配置文件读取
def load_config():
    config = {'MODEL_ID': 'zai-org/AutoGLM-Phone-9B'}
    if os.path.exists('deploy.config'):
        with open('deploy.config') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    return os.environ.get('MODEL_ID', config['MODEL_ID'])

MODEL_ID = load_config()
LOCAL_DIR = "model"

def main():
    print(f"下载模型: {MODEL_ID}")
    print(f"目标目录: {LOCAL_DIR}")
    
    snapshot_download(
        repo_id=MODEL_ID,
        local_dir=LOCAL_DIR,
        local_dir_use_symlinks=False
    )
    
    # 计算大小
    total_size = sum(
        os.path.getsize(os.path.join(dp, f))
        for dp, _, files in os.walk(LOCAL_DIR)
        for f in files
    )
    
    info = {
        "status": "completed",
        "model_id": MODEL_ID,
        "model_size_gb": total_size / 1024**3,
        "download_time": datetime.now().isoformat()
    }
    
    with open("model_download_info.json", "w") as f:
        json.dump(info, f, indent=2)
    
    print(f"\n✅ 下载完成: {info['model_size_gb']:.1f} GB")

if __name__ == "__main__":
    main()
