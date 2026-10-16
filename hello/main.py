from fastapi import FastAPI

app = FastAPI(title="AI NOR – hello")


@app.get("/")
def root():
    return {"app": "AI NOR", "status": "hello world"}


@app.get("/health")
def health():
    return {"ok": True}
