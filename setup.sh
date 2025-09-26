#!/bin/bash

# Обновляем pip
pip install --upgrade pip

# Ставим зависимости проекта
pip install --no-cache-dir -r requirements.txt

# Клонируем модели
git clone --depth 1 https://github.com/radekd91/emoca.git /opt/emoca
git clone --depth 1 https://github.com/yfeng95/DECA.git /opt/DECA
git clone --depth 1 https://github.com/Next3D/Next3D.git /opt/Next3D

# Ставим зависимости моделей
pip install --no-cache-dir -r /opt/emoca/requirements.txt || true
pip install --no-cache-dir -r /opt/DECA/requirements.txt || true
pip install --no-cache-dir -r /opt/Next3D/requirements.txt || true

# Скачиваем веса Next3D
mkdir -p /workspace/Next3D
wget -O /workspace/Next3D/next3d_ckpt.pth https://huggingface.co/Next3D/Next3D/resolve/main/next3d_ckpt.pth

echo "Setup complete. Run 'python3 server.py' to start the API."

