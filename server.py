# server.py
import os
import uuid
import time
import subprocess
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import zipfile

APP_ROOT = Path("/workspace")
INPUT_DIR = APP_ROOT / "input_images"
OUTPUTS_DIR = APP_ROOT / "outputs"

# Default commands
EMOCA_DEFAULT_CMD = os.environ.get(
    "EMOCA_CMD",
    "python3 /opt/emoca/demo.py --image {input} --output_folder {out}/emoca"
)
DECA_DEFAULT_CMD = os.environ.get(
    "DECA_CMD",
    "python3 /opt/DECA/deca.py --test=True --input_path {input} --output_path {out}/deca"
)
NEXT3D_DEFAULT_CMD = os.environ.get(
    "NEXT3D_CMD",
    "python3 /opt/Next3D/infer.py --img_path {input} --save_dir {out}/next3d --ckpt /workspace/Next3D/checkpoint.pth"
)
BLENDER_CMD = os.environ.get("BLENDER_CMD", "blender")

# Timeouts (seconds)
EMOCA_TIMEOUT = int(os.environ.get("EMOCA_TIMEOUT", "240"))
NEXT3D_TIMEOUT = int(os.environ.get("NEXT3D_TIMEOUT", "240"))
BLENDER_TIMEOUT = int(os.environ.get("BLENDER_TIMEOUT", "300"))

# baked resolution
BAKED_RES = int(os.environ.get("BAKED_RES", "2048"))

app = FastAPI(title="Face3D Pipeline")

def ensure_dirs():
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

def run_cmd(cmd, cwd=None, timeout=300, logfile=None):
    env = os.environ.copy()
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, text=True)
    out_lines = []
    start = time.time()
    try:
        while True:
            line = p.stdout.readline()
            if line:
                out_lines.append(line)
                if logfile:
                    with open(logfile, "a", encoding="utf-8") as f:
                        f.write(line)
            elif p.poll() is not None:
                break
            if time.time() - start > timeout:
                p.kill()
                raise TimeoutError(f"Command timed out after {timeout}s")
        return p.returncode, "".join(out_lines)
    except Exception:
        try:
            p.kill()
        except:
            pass
        raise

def find_first_obj(folder: Path):
    """Find first .obj file in a folder (including subfolders)."""
    if not folder.exists():
        return None
    objs = list(folder.rglob("*.obj"))
    return str(objs[0]) if objs else None

def zip_folder_contents(folder: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) a
