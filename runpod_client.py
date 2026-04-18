import os
import runpod
import logging
import asyncio
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Config
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

class RunPodClient:
    def __init__(self):
        if not RUNPOD_API_KEY and not MOCK_MODE:
            logger.warning("RUNPOD_API_KEY not set and MOCK_MODE is disabled")
        runpod.api_key = RUNPOD_API_KEY
        self.endpoint_id = RUNPOD_ENDPOINT_ID

    async def generate_music(self, prompt: str, duration: int) -> Dict[str, Any]:
        """
        Triggers a RunPod serverless job for Meta MusicGen.
        Supports MOCK_MODE for local testing/demonstration.
        """
        if MOCK_MODE:
            logger.info(f"[MOCK MODE] Simulating generation for: {prompt}")
            await asyncio.sleep(3) # Simulate processing time
            return {
                "status": "success", 
                "audio_url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", 
                "job_id": "mock_job_12345"
            }

        if not self.endpoint_id:
            logger.error("RUNPOD_ENDPOINT_ID is missing")
            return {"status": "error", "message": "RunPod Endpoint ID not configured"}

        try:
            # Initialize the endpoint
            endpoint = runpod.Endpoint(self.endpoint_id)

            logger.info(f"Triggering RunPod job with prompt: {prompt} ({duration}s)")
            
            # Send job to RunPod
            # Note: run().run() is usually blocking in the SDK but we can use run_sync or similar if available, 
            # or run it in a thread if needed. The newer SDK supports async triggers.
            job = endpoint.run({"input": {"prompt": prompt, "duration": duration}})
            
            # Non-blocking wait for job status
            while True:
                status = job.status()
                if status == "COMPLETED":
                    output = job.output()
                    logger.info(f"Job completed successfully. Output: {output}")
                    return {"status": "success", "audio_url": output.get("audio_url", ""), "job_id": job.job_id}
                elif status == "FAILED":
                    logger.error(f"Job {job.job_id} failed")
                    return {"status": "failed", "error": "Job failed on RunPod worker"}
                
                await asyncio.sleep(2) # Poll every 2 seconds
                
        except Exception as e:
            logger.exception(f"Exception during RunPod job: {str(e)}")
            return {"status": "error", "message": str(e)}

# Singleton instance
runpod_client = RunPodClient()
