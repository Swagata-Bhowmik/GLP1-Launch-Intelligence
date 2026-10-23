# Hugging Face Space (Docker SDK) for the GLP-1 Launch Intelligence Streamlit app.
# Built from the folder that deploy/build_space.py prepares; models are downloaded from the Hub at start-up.
FROM python:3.11-slim

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH HF_HOME=/home/user/.cache/huggingface \
    PYTHONPATH=/home/user/app/src PYTHONUNBUFFERED=1
WORKDIR /home/user/app

COPY --chown=user requirements-space.txt .
RUN pip install --no-cache-dir --user torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir --user -r requirements-space.txt

COPY --chown=user . .

EXPOSE 7860
CMD python deploy/fetch_models.py && \
    streamlit run app/app.py --server.port 7860 --server.address 0.0.0.0 --server.headless true \
    --browser.gatherUsageStats false
