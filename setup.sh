#!/bin/bash
set -e

echo "=== Step 1: Устанавливаем Python зависимости ==="
pip3 install --no-cache-dir -r /workspace/requirements.txt

echo "=== Step 2: Создаём необходимые директории ==="
mkdir -p /workspace/input_images
mkdir -p /workspace/outputs
mkdir -p /workspace/models

echo "=== Step 3: Скачиваем EMOCA модель ==="
if [ ! -f /workspace/models/emoca_model.zip ]; then
    wget -O /workspace/models/emoca_model.zip https://emoca.is.tue.mpg.de/emoca_model.zip
    unzip -o /workspace/models/emoca_model.zip -d /opt/emoca
fi

echo "=== Step 4: Скачиваем DECA модель ==="
if [ ! -f /workspace/models/deca_model.tar ]; then
    wget -O /workspace/models/deca_model.tar https://github.com/YadiraF/DECA/releases/download/v1.0/DECA_model.tar
    tar -xf /workspace/models/deca_model.tar -C /opt/DECA
fi

echo "=== Step 5: Скачиваем Next3D чекпоинт ==="
if [ ! -f /workspace/models/next3d_ckpt.pth ]; then
    wget -O /workspace/models/next3d_ckpt.pth https://huggingface.co/Next3D/Next3D/resolve/main/next3d_ckpt.pth
fi

echo "=== Step 6: Проверка Blender ==="
if ! command -v blender &> /dev/null; then
    echo "Blender не найден! Скачиваем и устанавливаем Blender 3.6"
    wget https://download.blender.org/release/Blender3.6/blender-3.6.15-linux-x64.tar.xz -O /workspace/blender.tar.xz
    tar -xJf /workspace/blender.tar.xz -C /opt
    ln -sf /opt/blender-3.6.15-linux-x64/blender /usr/local/bin/blender
fi

echo "=== Step 7: Setup finished ==="
