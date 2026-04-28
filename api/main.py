from fastapi import FastAPI

app = FastAPI(title="Rules Lookup API")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
