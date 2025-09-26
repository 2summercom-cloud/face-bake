# Dockerfile
FROM nvidia/cuda:12.2.2-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y wget git python3 python3-pip build-essential \
    libglu1-mesa libxi6 libxrender1 libxkbcommon0 libsm6 libxext6 \
    xvfb ca-certificates ffmpeg unzip && \
    rm -rf /var/lib/apt/lists/*

# Install Blender 3.6 LTS
RUN wget https://download.blender.org/release/Blender3.6/blender-3.6.15-linux-x64.tar.xz && \
    tar -xJf blender-3.6.15-linux-x64.tar.xz && \
    mv blender-3.6.15-linux-x64 /opt/blender && \
    ln -s /opt/blender/blender /usr/local/bin/blender && \
    chmod +x /usr/local/bin/blender

WORKDIR /workspace

# Copy project files
COPY . /workspace

# Install PyTorch with CUDA 12.x support
RUN pip3 install --no-cache-dir torch==2.1.0 torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cu121

# Install FastAPI and helpers
RUN pip3 install --no-cache-dir -r requirements.txt

# Clone and setup EMOCA / DECA / Next3D
RUN git clone --depth 1 https://github.com/radekd91/emoca.git /opt/emoca && \
    git clone --depth 1 https://github.com/yfeng95/DECA.git /opt/DECA && \
    git clone --depth 1 https://github.com/Next3D/Next3D.git /opt/Next3D

# Install additional requirements
RUN pip3 install --no-cache-dir -r /opt/emoca/requirements.txt || true
RUN pip3 install --no-cache-dir -r /opt/DECA/requirements.txt || true
RUN pip3 install --no-cache-dir -r /opt/Next3D/requirements.txt || true

# Download pretrained weights
RUN mkdir -p /workspace/models && \
    wget -O /workspace/models/emoca_weights.zip https://emoca.is.tue.mpg.de/emoca_model.zip && \
    unzip /workspace/models/emoca_weights.zip -d /opt/emoca && \
    wget -O /workspace/models/deca_model.tar https://github.com/YadiraF/DECA/releases/download/v1.0/DECA_model.tar && \
    tar -xf /workspace/models/deca_model.tar -C /opt/DECA && \
    wget -O /workspace/models/next3d_ckpt.pth https://huggingface.co/Next3D/Next3D/resolve/main/next3d_ckpt.pth

EXPOSE 8000

# Start API server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
