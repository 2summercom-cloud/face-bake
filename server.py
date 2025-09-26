from fastapi import FastAPI, UploadFile, File
import uvicorn
import bake  # наш bake.py с логикой обработки

app = FastAPI()

@app.post("/process")
async def process_face(file: UploadFile = File(...)):
    # сохраняем загруженное фото
    with open("input.jpg", "wb") as f:
        f.write(await file.read())

    # вызываем функцию из bake.py
    output_path = bake.run("input.jpg")

    return {"result": output_path}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
