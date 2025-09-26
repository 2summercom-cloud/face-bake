# Dockerfile
FROM nvidia/cuda:12.2.2-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y wget git python3 python3-pip build-essential \
    libglu1-mesa libxi6 libxrender1 libxkbcommon0 libsm6 libxext6 \
    xvfb ca-certificates ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Install Blender 3.6 LTS
RUN wget https://download.blender.org/release/Blender3.6/blender-3.6.15-linux-x64.tar.xz && \
    tar -xJf blender-3.6.15-linux-x64.tar.xz && \
    mv blender-3.6.15-linux-x64 /opt/blender && \
    ln -s /opt/blender/blender /usr/local/bin/blender

WORKDIR /workspace

# Copy project files
COPY . /workspace

# Install Python deps (API + utils). Heavy ML deps like torch/EMOCA/Next3D will be attempted below.
RUN pip3 install --no-cache-dir -r requirements.txt

# Clone EMOCA / DECA / Next3D (if internet available). If clone fails, build continues.
RUN set -eux; \
    if [ ! -d /opt/emoca ]; then git clone --depth 1 https://github.com/radekd91/emoca.git /opt/emoca || true; fi; \
    if [ ! -d /opt/DECA ]; then git clone --depth 1 https://github.com/yfeng95/DECA.git /opt/DECA || true; fi; \
    if [ ! -d /opt/Next3D ]; then git clone --depth 1 https://github.com/Next3D/Next3D.git /opt/Next3D || true

# Try to install ML requirements from those repos if they have requirements.txt. Do not fail build if they fail.
RUN set -eux; \
    if [ -f /opt/emoca/requirements.txt ]; then pip3 install --no-cache-dir -r /opt/emoca/requirements.txt || echo "emoca reqs install failed"; fi; \
    if [ -f /opt/DECA/requirements.txt ]; then pip3 install --no-cache-dir -r /opt/DECA/requirements.txt || echo "deca reqs install failed"; fi; \
    if [ -f /opt/Next3D/requirements.txt ]; then pip3 install --no-cache-dir -r /opt/Next3D/requirements.txt || echo "next3d reqs install failed"; fi

# NOTE:
# If auto-install of torch fails due to CUDA/driver mismatch, you must install the correct torch wheel manually
# (or use a prebuilt image). See README in repo for guidance.

EXPOSE 8000

# Start API server (uvicorn) on container start
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
