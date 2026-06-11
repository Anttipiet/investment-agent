from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api_routes import router as api_router

app = FastAPI(
    title="Investment Agent API",
    version="2.0",
    description="Professional investment intelligence platform with Phase 1 + Phase 2 analysis"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include API routes
app.include_router(api_router)

@app.get("/")
def root():
    return {
        'name': 'Investment Agent API',
        'version': '2.0',
        'endpoints': {
            'signals': '/api/signals/generate/{symbol}',
            'valuation': '/api/valuation/{symbol}',
            'earnings': '/api/earnings/{symbol}',
            'macro': '/api/macro/summary',
            'intelligence': '/api/intelligence/{symbol}'
        }
    }

@app.get("/docs")
def docs():
    return {
        'message': 'Visit http://localhost:8000/docs for interactive API documentation'
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)