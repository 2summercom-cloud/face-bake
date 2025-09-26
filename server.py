from fastapi import FastAPI, UploadFile, File
import uvicorn
import subprocess
import os

app = FastAPI()

@app.post("/process")
async def process_face(file: UploadFile = File(...)):
    # сохраняем загруженное фото (например, как emoca.obj пока для теста)
    input_path = "/workspace/emoca.obj"
    with open(input_path, "wb") as f:
        f.write(await file.read())

    # вызываем Blender с нашим bake.py
    cmd = [
        "blender", "-b", "--python", "bake.py"
    ]
    subprocess.run(cmd, check=True)

    output_path = "/workspace/final_texture.png"
    if os.path.exists(output_path):
        return {"result": output_path}
    else:
        return {"error": "Bake failed"}
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
