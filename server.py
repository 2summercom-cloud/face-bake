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

# Timeouts
EMOCA_TIMEOUT = int(os.environ.get("EMOCA_TIMEOUT", "240"))
NEXT3D_TIMEOUT = int(os.environ.get("NEXT3D_TIMEOUT", "240"))
BLENDER_TIMEOUT = int(os.environ.get("BLENDER_TIMEOUT", "300"))

# Baked resolution
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
    if not folder.exists():
        return None
    objs = list(folder.rglob("*.obj"))
    return str(objs[0]) if objs else None

def zip_folder_contents(folder: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in folder.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(folder))

def check_weights():
    missing = []
    if not Path("/opt/emoca/emoca_model.pth").exists():
        missing.append("EMOCA weights missing")
    if not Path("/opt/DECA/DECA_model.pth").exists():
        missing.append("DECA weights missing")
    if not Path("/workspace/Next3D/checkpoint.pth").exists():
        missing.append("Next3D weights missing")
    if missing:
        raise RuntimeError("Missing model weights: " + ", ".join(missing))

@app.post("/process")
async def process_face(file: UploadFile = File(...)):
    ensure_dirs()
    check_weights()
    job_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    job_dir = OUTPUTS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = job_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Save uploaded image
    input_path = INPUT_DIR / f"{job_id}_input.jpg"
    with open(input_path, "wb") as f:
        f.write(await file.read())

    # EMOCA / DECA
    emoca_dir = job_dir / "emoca_out"
    emoca_dir.mkdir(exist_ok=True)
    emoca_log = logs_dir / "emoca.log"
    emoca_cmd = EMOCA_DEFAULT_CMD.format(input=str(input_path), out=str(job_dir))
    try:
        ret, _ = run_cmd(emoca_cmd.split(), logfile=str(emoca_log), timeout=EMOCA_TIMEOUT)
        if ret != 0:
            deca_dir = job_dir / "deca_out"
            deca_dir.mkdir(exist_ok=True)
            deca_log = logs_dir / "deca.log"
            deca_cmd = DECA_DEFAULT_CMD.format(input=str(input_path), out=str(job_dir))
            ret2, _ = run_cmd(deca_cmd.split(), logfile=str(deca_log), timeout=EMOCA_TIMEOUT)
            if ret2 != 0:
                raise RuntimeError("Both EMOCA and DECA failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    emoca_obj = find_first_obj(emoca_dir) or find_first_obj(job_dir / "deca")
    if not emoca_obj:
        raise HTTPException(status_code=500, detail="No .obj produced by EMOCA/DECA")

    # Next3D
    next3d_dir = job_dir / "next3d_out"
    next3d_dir.mkdir(exist_ok=True)
    next3d_log = logs_dir / "next3d.log"
    next3d_cmd = NEXT3D_DEFAULT_CMD.format(input=str(input_path), out=str(job_dir))
    try:
        ret, _ = run_cmd(next3d_cmd.split(), logfile=str(next3d_log), timeout=NEXT3D_TIMEOUT)
        if ret != 0:
            raise RuntimeError("Next3D failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    next3d_obj = find_first_obj(next3d_dir) or emoca_obj

    # Blender bake
    final_tex = job_dir / "final_texture.png"
    final_obj = job_dir / "final_emoca.obj"
    blender_log = logs_dir / "blender.log"
    blender_cmd = [
        BLENDER_CMD, "-b", "--python", "/workspace/bake.py", "--",
        emoca_obj, next3d_obj, str(final_tex), str(final_obj), str(BAKED_RES)
    ]
    try:
        ret, _ = run_cmd(blender_cmd, logfile=str(blender_log), timeout=BLENDER_TIMEOUT)
        if ret != 0:
            raise RuntimeError("Blender bake failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Package outputs
    zip_path = job_dir / "result.zip"
    zip_folder_contents(job_dir, zip_path)
    if not zip_path.exists():
        raise HTTPException(status_code=500, detail="Zip packaging failed")

    return FileResponse(path=str(zip_path), filename=f"{job_id}_result.zip", media_type="application/zip")
