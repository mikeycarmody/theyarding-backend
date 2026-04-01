from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "The Yarding backend is running"}