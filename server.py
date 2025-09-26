from fastapi import FastAPI, UploadFile, File
import uvicorn
import subprocess
import os

app = FastAPI()

@app.post("/process")
async def process_face(file: UploadFile = File(...)):
    # сохраняем загруженный файл как emoca.obj
    input_path = "/workspace/emoca.obj"
    with open(input_path, "wb") as f:
        f.write(await file.read())

    # Запускаем Blender с bake.py
    cmd = ["blender", "-b", "--python", "/workspace/bake.py"]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        return {"error": f"Blender failed: {str(e)}"}

    output_path = "/workspace/final_texture.png"
    if os.path.exists(output_path):
        return {"result": output_path}
    else:
        return {"error": "No output generated"}
    

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
