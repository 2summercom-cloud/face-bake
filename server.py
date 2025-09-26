# server.py
import os
import shutil
import uuid
import time
import subprocess
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import asyncio
import zipfile

APP_ROOT = Path("/workspace")
INPUT_DIR = APP_ROOT / "input_images"
OUTPUTS_DIR = APP_ROOT / "outputs"
EMOCA_DEFAULT_CMD = os.environ.get(
    "EMOCA_CMD",
    "python3 /opt/emoca/demo.py --image {input} --out {out}/emoca"
)
DECA_DEFAULT_CMD = os.environ.get(
    "DECA_CMD",
    "python3 /opt/DECA/demo.py --input_path {input} --output_dir {out}/deca"
)
NEXT3D_DEFAULT_CMD = os.environ.get(
    "NEXT3D_CMD",
    "python3 /opt/Next3D/infer.py --img {input} --out {out}/next3d"
)
BLENDER_CMD = os.environ.get("BLENDER_CMD", "blender")

# timeouts (seconds)
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
    """Run command, stream to logfile if provided, return (returncode, stdout+stderr)"""
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
            # timeout check
            if time.time() - start > timeout:
                p.kill()
                raise TimeoutError(f"Command timed out after {timeout}s")
        ret = p.returncode
        return ret, "".join(out_lines)
    except Exception as e:
        try:
            p.kill()
        except:
            pass
        raise

def find_first_obj(folder: Path):
    if not folder.exists():
        return None
    for p in folder.rglob("*.obj"):
        return str(p)
    return None

def zip_folder_contents(folder: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in folder.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(folder))

@app.post("/process")
async def process_face(file: UploadFile = File(...)):
    """
    Full pipeline:
    1) Save uploaded photo
    2) Run EMOCA or DECA to produce emoca.obj
    3) Run Next3D to produce next3d.obj
    4) Run Blender bake.py to bake texture from next3d -> emoca (outputs final_texture.png and final_emoca.obj)
    5) Return ZIP with outputs
    """
    ensure_dirs()
    job_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    job_dir = OUTPUTS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = job_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    # 1) save uploaded image
    input_path = INPUT_DIR / f"{job_id}_input.jpg"
    with open(input_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # 2) Run EMOCA (try EMOCA, fallback to DECA)
    emoca_out_dir = job_dir / "emoca_out"
    emoca_out_dir.mkdir(exist_ok=True)
    emoca_log = logs_dir / "emoca.log"
    emoca_cmd_template = EMOCA_DEFAULT_CMD
    emoca_cmd = emoca_cmd_template.format(input=str(input_path), out=str(job_dir))
    try:
        # run EMOCA
        ret, out = run_cmd(emoca_cmd.split(), logfile=str(emoca_log), timeout=EMOCA_TIMEOUT)
        if ret != 0:
            # try DECA fallback
            deca_log = logs_dir / "deca.log"
            deca_cmd = DECA_DEFAULT_CMD.format(input=str(input_path), out=str(job_dir))
            ret2, out2 = run_cmd(deca_cmd.split(), logfile=str(deca_log), timeout=EMOCA_TIMEOUT)
            if ret2 != 0:
                raise RuntimeError("Both EMOCA and DECA failed; check logs.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"EMOCA/DECA step failed: {e}")

    # find emoca.obj in job_dir (search)
    emoca_obj = find_first_obj(job_dir)
    if not emoca_obj:
        raise HTTPException(status_code=500, detail="No .obj produced by EMOCA/DECA. Check logs.")

    # 3) Run Next3D
    next3d_log = logs_dir / "next3d.log"
    next3d_cmd = NEXT3D_DEFAULT_CMD.format(input=str(input_path), out=str(job_dir))
    try:
        ret, out = run_cmd(next3d_cmd.split(), logfile=str(next3d_log), timeout=NEXT3D_TIMEOUT)
        if ret != 0:
            raise RuntimeError("Next3D command returned non-zero exit code.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Next3D step failed: {e}")

    # find next3d.obj
    next3d_obj = find_first_obj(job_dir)
    # make sure it's not the same as emoca_obj (we search again)
    # prefer file inside next3d folder if Next3D creates subfolder
    possible = list((job_dir).rglob("next3d*.obj")) + list((job_dir).rglob("*/next3d*.obj"))
    if possible:
        next3d_obj = str(possible[0])
    else:
        # fallback: take any obj different from emoca_obj
        found = [str(p) for p in job_dir.rglob("*.obj")]
        next3d_obj = None
        for f in found:
            if f != emoca_obj:
                next3d_obj = f
                break
    if not next3d_obj:
        # Allow using emoca_obj for both (less ideal)
        next3d_obj = emoca_obj

    # 4) Run Blender bake
    # outputs
    final_tex = job_dir / "final_texture.png"
    final_obj = job_dir / "final_emoca.obj"
    blender_log = logs_dir / "blender.log"
    # call blender with bake.py; pass args after --
    blender_cmd = [
        BLENDER_CMD, "-b", "--python", "/workspace/bake.py", "--",
        emoca_obj, next3d_obj, str(final_tex), str(final_obj), str(BAKED_RES)
    ]
    try:
        ret, out = run_cmd(blender_cmd, logfile=str(blender_log), timeout=BLENDER_TIMEOUT)
        if ret != 0:
            raise RuntimeError("Blender bake returned non-zero exit code.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Blender bake failed: {e}")

    # 5) collect outputs and zip
    # expected outputs: final_texture.png, final_emoca.obj (and mtl)
    zip_path = job_dir / "result.zip"
    zip_folder_contents(job_dir, zip_path)

    if not zip_path.exists():
        raise HTTPException(status_code=500, detail="Packaging failed, no zip produced.")

    return FileResponse(path=str(zip_path), filename=f"{job_id}_result.zip", media_type="application/zip")
