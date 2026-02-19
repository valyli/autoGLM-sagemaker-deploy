"""Universal vLLM Inference Handler for SageMaker"""

import subprocess
import time
import os
import json
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
import uvicorn

vllm_process = None

# 从环境变量读取配置（由 SageMaker 传入）
SERVED_MODEL_NAME = os.environ.get('SERVED_MODEL_NAME', 'model')
MAX_MODEL_LEN = os.environ.get('MAX_MODEL_LEN', '4096')
DTYPE = os.environ.get('DTYPE', 'auto')
MODEL_TYPE = os.environ.get('MODEL_TYPE', 'text')  # text, multimodal


def start_vllm_server() -> bool:
    """Start vLLM server with configurable parameters"""
    global vllm_process
    
    model_path = "/opt/ml/model"
    
    # 基础参数（所有模型通用）
    cmd = [
        "python3", "-m", "vllm.entrypoints.openai.api_server",
        "--model", model_path,
        "--served-model-name", SERVED_MODEL_NAME,
        "--max-model-len", MAX_MODEL_LEN,
        "--dtype", DTYPE,
        "--trust-remote-code",
        "--host", "127.0.0.1",
        "--port", "8000",
    ]
    
    # 多模态参数（仅当 MODEL_TYPE=multimodal 时添加）
    if MODEL_TYPE == 'multimodal':
        cmd.extend([
            "--allowed-local-media-path", "/",
            "--mm-encoder-tp-mode", "data",
            "--mm-processor-cache-type", "shm",
            "--mm-processor-kwargs", '{"max_pixels": 5000000}',
            "--chat-template-content-format", "string",
            "--limit-mm-per-prompt", '{"image": 10}',
        ])
    
    env = os.environ.copy()
    env["VLLM_WORKER_MULTIPROC_METHOD"] = "spawn"
    
    print(f"Starting vLLM server with config:")
    print(f"  Model Name: {SERVED_MODEL_NAME}")
    print(f"  Max Length: {MAX_MODEL_LEN}")
    print(f"  Data Type: {DTYPE}")
    print(f"  Model Type: {MODEL_TYPE}")
    print(f"Command: {' '.join(cmd)}")
    
    vllm_process = subprocess.Popen(cmd, env=env)
    
    for _ in range(120):
        try:
            resp = httpx.get("http://127.0.0.1:8000/health", timeout=5)
            if resp.status_code == 200:
                print("vLLM server ready")
                return True
        except:
            pass
        time.sleep(5)
    
    print("vLLM server failed to start")
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if not start_vllm_server():
        raise RuntimeError("Failed to start vLLM server")
    yield
    # Shutdown
    if vllm_process:
        vllm_process.terminate()


app = FastAPI(title="Universal vLLM Inference Server", lifespan=lifespan)


@app.get("/ping")
async def ping():
    return Response(status_code=200)


@app.post("/invocations")
async def invoke(request: Request):
    data = await request.json()
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post("http://127.0.0.1:8000/v1/chat/completions", json=data)
        return JSONResponse(resp.json())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
