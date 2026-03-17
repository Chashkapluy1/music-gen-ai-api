import logging
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from auth import get_current_user, ClerkUser
from runpod_client import runpod_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MusicGenAPI")

app = FastAPI(
    title="Production-Ready Music Generation API",
    description="API for high-quality music generation using Meta MusicGen via RunPod",
    version="1.0.0"
)

# Request Models
class GenerationRequest(BaseModel):
    prompt: str = Field(..., example="80s synthwave with a catchy melody")
    duration: int = Field(default=10, ge=1, le=30, description="Duration in seconds")

class GenerationResponse(BaseModel):
    status: str
    audio_url: str
    job_id: str

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Music Generation API"}

@app.post("/generate", response_model=GenerationResponse)
async def generate_music(
    request: GenerationRequest,
    user: ClerkUser = Depends(get_current_user)
):
    """
    Generate music based on a text prompt.
    Requires Clerk Authentication.
    """
    logger.info(f"Received generation request from user {user.user_id}: {request.prompt}")
    
    # Trigger RunPod Job
    result = await runpod_client.generate_music(request.prompt, request.duration)
    
    if result.get("status") != "success":
        logger.error(f"Generation failed for user {user.user_id}: {result.get('message', 'Unknown error')}")
        raise HTTPException(
            status_code=500, 
            detail=f"Music generation failed: {result.get('message', 'Internal server error')}"
        )
    
    logger.info(f"Successfully generated music for user {user.user_id}. Job ID: {result['job_id']}")
    
    return GenerationResponse(
        status="success",
        audio_url=result["audio_url"],
        job_id=result["job_id"]
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
