#!/bin/bash

set -e  # выйти при любой ошибке

# Обновление pip
python3 -m pip install --upgrade pip

# Установка зависимостей проекта
pip3 install --no-cache-dir -r requirements.txt

# Установка зависимостей EMOCA, DECA, Next3D
pip3 install --no-cache-dir -r /opt/emoca/requirements.txt || true
pip3 install --no-cache-dir -r /opt/DECA/requirements.txt || true
pip3 install --no-cache-dir -r /opt/Next3D/requirements.txt || true

# Создание папок для входных/выходных данных
mkdir -p /workspace/input_images
mkdir -p /workspace/outputs
mkdir -p /workspace/models

# Скачивание предобученных моделей
if [ ! -f /workspace/models/emoca_model.zip ]; then
    wget -O /workspace/models/emoca_model.zip https://emoca.is.tue.mpg.de/emoca_model.zip
    unzip /workspace/models/emoca_model.zip -d /opt/emoca
fi

if [ ! -f /workspace/models/deca_model.tar ]; then
    wget -O /workspace/models/deca_model.tar https://github.com/YadiraF/DECA/releases/download/v1.0/DECA_model.tar
    tar -xf /workspace/models/deca_model.tar -C /opt/DECA
fi

if [ ! -f /workspace/models/next3d_ckpt.pth ]; then
    wget -O /workspace/models/next3d_ckpt.pth https://huggingface.co/Next3D/Next3D/resolve/main/next3d_ckpt.pth
fi

echo "Setup finished."

