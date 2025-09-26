# Базовый образ с Blender
FROM nvidia/cuda:12.2.2-devel-ubuntu22.04

# Установка зависимостей
RUN apt-get update && \
    apt-get install -y wget git python3 python3-pip \
    libglu1-mesa libxi6 libxrender1 libxkbcommon0 \
    libsm6 libxext6 xvfb

# Ставим Blender (LTS 3.6)
RUN wget https://download.blender.org/release/Blender3.6/blender-3.6.15-linux-x64.tar.xz && \
    tar -xJf blender-3.6.15-linux-x64.tar.xz && \
    mv blender-3.6.15-linux-x64 /opt/blender && \
    ln -s /opt/blender/blender /usr/local/bin/blender

# Копируем скрипт bake.py внутрь контейнера
WORKDIR /workspace
COPY bake.py /workspace/bake.py

# По умолчанию запускаем Blender в headless
ENTRYPOINT ["blender", "--background", "--python", "/workspace/bake.py"]
