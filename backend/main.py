from fastapi import FastAPI

app = FastAPI(
    title="ALFARES AI API"
)

@app.get("/")
def root():
    return {
        "project":"ALFARES_SYSTEM_PROGRAMY",
        "version":"2026"
    }

@app.get("/health")
def health():
    return {
        "status":"online"
    }
