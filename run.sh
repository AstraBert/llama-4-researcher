eval "$(conda shell.bash hook)"

conda activate llama-4-researcher
cd /app/
uvicorn api:app --host 0.0.0.0 --port 80
conda deactivate
