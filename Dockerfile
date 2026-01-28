# Custom vLLM Container for AutoGLM-Phone-9B on SageMaker
FROM --platform=linux/amd64 vllm/vllm-openai:v0.14.1

# Use HF_HOME instead of deprecated TRANSFORMERS_CACHE
ENV HF_HOME=/tmp/hf_home
ENV VLLM_WORKER_MULTIPROC_METHOD=spawn

RUN pip install --no-cache-dir httpx uvicorn fastapi

COPY code/model.py /opt/ml/code/model.py

EXPOSE 8080

ENTRYPOINT ["python3", "/opt/ml/code/model.py"]
