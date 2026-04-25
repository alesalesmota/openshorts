import os
import uuid
import subprocess
import threading
import json
import shutil
import glob
import time
import asyncio
import sys
from urllib.parse import urlparse
from dotenv import load_dotenv
from typing import Dict, Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

# Constants
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "output"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configuration
# Default to 1 if not set, but user can set higher for powerful servers
MAX_CONCURRENT_JOBS = int(os.environ.get("MAX_CONCURRENT_JOBS", "5"))
MAX_FILE_SIZE_MB = 2048  # 2GB limit
JOB_RETENTION_SECONDS = 3600  # 1 hour retention

# Application State
job_queue = asyncio.Queue()
jobs: Dict[str, Dict] = {}
# Semaphore to limit concurrency to MAX_CONCURRENT_JOBS
concurrency_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)

AI_HEADER_MAP = {
    "AI_PROVIDER": "X-AI-Provider",
    "AI_MODEL": "X-AI-Model",
    "AI_API_KEY": "X-AI-API-Key",
    "AI_BASE_URL": "X-AI-Base-URL",
    "AZURE_OPENAI_ENDPOINT": "X-Azure-OpenAI-Endpoint",
    "AZURE_OPENAI_DEPLOYMENT": "X-Azure-OpenAI-Deployment",
    "AZURE_OPENAI_API_VERSION": "X-Azure-OpenAI-API-Version",
}

MODEL_SORT_OPTIONS = [
    {"value": "recommended", "label": "Recommended"},
    {"value": "cheapest", "label": "Cheapest first"},
    {"value": "smartest", "label": "Smartest first"},
    {"value": "newest", "label": "Newest first"},
    {"value": "fastest", "label": "Fastest first"},
]

MODEL_CATALOG = {
    "gemini": [
        {
            "id": "gemini-2.5-flash",
            "model": "gemini-2.5-flash",
            "label": "Gemini 2.5 Flash",
            "cost_label": "Free tier / paid after quota",
            "credit_label": "Google AI Studio free tier can apply",
            "quality_label": "Fast, strong default",
            "status_label": "Recommended",
            "cost_rank": 1,
            "intelligence_rank": 72,
            "speed_rank": 1,
            "release_date": "2025-06-01",
        },
        {
            "id": "gemini-2.5-pro",
            "model": "gemini-2.5-pro",
            "label": "Gemini 2.5 Pro",
            "cost_label": "Free tier / paid after quota",
            "credit_label": "Higher usage usually costs more",
            "quality_label": "Deeper reasoning",
            "status_label": "High quality",
            "cost_rank": 4,
            "intelligence_rank": 88,
            "speed_rank": 4,
            "release_date": "2025-06-01",
        },
    ],
    "openai": [
        {
            "id": "gpt-4.1-nano",
            "model": "gpt-4.1-nano",
            "label": "GPT-4.1 Nano",
            "cost_label": "Paid API tokens",
            "credit_label": "May use account credits if available",
            "quality_label": "Very cheap, lightweight",
            "status_label": "Budget",
            "cost_rank": 1,
            "intelligence_rank": 48,
            "speed_rank": 1,
            "release_date": "2025-04-14",
        },
        {
            "id": "gpt-4.1-mini",
            "model": "gpt-4.1-mini",
            "label": "GPT-4.1 Mini",
            "cost_label": "Paid API tokens",
            "credit_label": "May use account credits if available",
            "quality_label": "Good low-cost clip analysis",
            "status_label": "Recommended",
            "cost_rank": 2,
            "intelligence_rank": 72,
            "speed_rank": 2,
            "release_date": "2025-04-14",
        },
        {
            "id": "gpt-4.1",
            "model": "gpt-4.1",
            "label": "GPT-4.1",
            "cost_label": "Paid API tokens",
            "credit_label": "May use account credits if available",
            "quality_label": "Higher quality, higher cost",
            "status_label": "High quality",
            "cost_rank": 5,
            "intelligence_rank": 84,
            "speed_rank": 4,
            "release_date": "2025-04-14",
        },
    ],
    "openrouter": [
        {
            "id": "openrouter/free",
            "model": "openrouter/free",
            "label": "OpenRouter Free Router",
            "cost_label": "Free models only",
            "credit_label": "Free tier rate limits apply",
            "quality_label": "Routes to a compatible free model",
            "status_label": "Free",
            "cost_rank": 0,
            "intelligence_rank": 45,
            "speed_rank": 3,
            "release_date": "2026-02-01",
        },
        {
            "id": "openai/gpt-4o-mini",
            "model": "openai/gpt-4o-mini",
            "label": "OpenAI GPT-4o Mini",
            "cost_label": "Paid OpenRouter credits",
            "credit_label": "Provider/account credits may apply",
            "quality_label": "Cheap general fallback",
            "status_label": "Budget",
            "cost_rank": 2,
            "intelligence_rank": 66,
            "speed_rank": 2,
            "release_date": "2024-07-18",
        },
    ],
    "nvidia-nim": [
        {
            "id": "meta/llama-3.1-70b-instruct",
            "model": "meta/llama-3.1-70b-instruct",
            "label": "Llama 3.1 70B Instruct",
            "cost_label": "NVIDIA credits/quota",
            "credit_label": "Developer credits may apply",
            "quality_label": "Open model, strong enough for transcripts",
            "status_label": "Recommended",
            "cost_rank": 2,
            "intelligence_rank": 70,
            "speed_rank": 3,
            "release_date": "2024-07-23",
        },
    ],
}

def build_ai_env(request: Request, require_key: bool = True) -> Dict[str, str]:
    ai_env: Dict[str, str] = {}
    legacy_gemini_key = request.headers.get("X-Gemini-Key")

    for env_key, header_name in AI_HEADER_MAP.items():
        value = request.headers.get(header_name) or os.environ.get(env_key)
        if value:
            ai_env[env_key] = value

    if legacy_gemini_key:
        ai_env["AI_PROVIDER"] = "gemini"
        ai_env["AI_API_KEY"] = legacy_gemini_key
        ai_env["GEMINI_API_KEY"] = legacy_gemini_key
    elif ai_env.get("AI_PROVIDER", os.environ.get("AI_PROVIDER", "")).lower() == "gemini":
        gemini_key = ai_env.get("AI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            ai_env["GEMINI_API_KEY"] = gemini_key

    if "AI_PROVIDER" not in ai_env and os.environ.get("GEMINI_API_KEY"):
        ai_env["AI_PROVIDER"] = "gemini"
        ai_env["AI_API_KEY"] = os.environ["GEMINI_API_KEY"]
        ai_env["GEMINI_API_KEY"] = os.environ["GEMINI_API_KEY"]

    if require_key and not ai_env.get("AI_API_KEY"):
        raise HTTPException(status_code=400, detail="Missing AI API key. Send X-AI-API-Key or legacy X-Gemini-Key.")

    return ai_env

def _model_option(provider: str, metadata: Dict, *, deployment: Optional[str] = None, version: Optional[str] = None, source: str = "catalog") -> Dict:
    model = metadata.get("model") or metadata.get("id") or deployment or ""
    option_id = deployment or metadata.get("id") or model
    return {
        "id": option_id,
        "provider": provider,
        "model": model,
        "deployment": deployment,
        "label": metadata.get("label") or model,
        "version": version or metadata.get("version") or "",
        "source": source,
        "selectable": True,
        "functional": True,
        "cost_label": metadata.get("cost_label") or "Provider billing applies",
        "credit_label": metadata.get("credit_label") or "Credit status depends on provider account",
        "quality_label": metadata.get("quality_label") or "General purpose",
        "status_label": metadata.get("status_label") or "Available",
        "cost_rank": metadata.get("cost_rank", 99),
        "intelligence_rank": metadata.get("intelligence_rank", 0),
        "speed_rank": metadata.get("speed_rank", 99),
        "release_date": metadata.get("release_date") or version or "",
    }


def _metadata_for_model(provider: str, model: str) -> Dict:
    compact = (model or "").lower()
    for item in MODEL_CATALOG.get(provider, []):
        if compact in {item.get("id", "").lower(), item.get("model", "").lower()}:
            return item

    if "gpt-4.1-mini" in compact or "gpt-4-1-mini" in compact:
        return {
            "id": model,
            "model": "gpt-4.1-mini",
            "label": "GPT-4.1 Mini",
            "cost_label": "Paid Azure credits",
            "credit_label": "Uses Azure OpenAI pay-as-you-go credits",
            "quality_label": "Good low-cost clip analysis",
            "status_label": "Ready",
            "cost_rank": 2,
            "intelligence_rank": 72,
            "speed_rank": 2,
            "release_date": "2025-04-14",
        }
    if "gpt-4.1-nano" in compact or "gpt-4-1-nano" in compact:
        return {
            "id": model,
            "model": "gpt-4.1-nano",
            "label": "GPT-4.1 Nano",
            "cost_label": "Paid Azure credits",
            "credit_label": "Uses Azure OpenAI pay-as-you-go credits",
            "quality_label": "Very cheap, lightweight",
            "status_label": "Budget",
            "cost_rank": 1,
            "intelligence_rank": 48,
            "speed_rank": 1,
            "release_date": "2025-04-14",
        }
    if "gpt-4o-mini" in compact:
        return {
            "id": model,
            "model": "gpt-4o-mini",
            "label": "GPT-4o Mini",
            "cost_label": "Paid Azure credits",
            "credit_label": "Uses Azure OpenAI pay-as-you-go credits",
            "quality_label": "Low-cost general model",
            "status_label": "Legacy/budget",
            "cost_rank": 2,
            "intelligence_rank": 64,
            "speed_rank": 2,
            "release_date": "2024-07-18",
        }
    return {
        "id": model,
        "model": model,
        "label": model,
        "cost_label": "Provider billing applies",
        "credit_label": "Credit status depends on provider account",
        "quality_label": "Not ranked yet",
        "status_label": "Available",
        "cost_rank": 50,
        "intelligence_rank": 50,
        "speed_rank": 50,
        "release_date": "",
    }


def _az_command_path() -> str:
    default_path = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
    return default_path if os.path.exists(default_path) else "az"


def _azure_account_name_from_endpoint() -> str:
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT") or os.environ.get("AI_BASE_URL") or ""
    host = urlparse(endpoint).netloc
    return host.split(".")[0] if host else ""


def _azure_deployment_options() -> List[Dict]:
    resource_group = os.environ.get("AZURE_OPENAI_RESOURCE_GROUP") or os.environ.get("AZURE_RESOURCE_GROUP") or ""
    account_name = os.environ.get("AZURE_OPENAI_ACCOUNT_NAME") or _azure_account_name_from_endpoint()
    current_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT") or os.environ.get("AI_MODEL") or ""
    options: List[Dict] = []

    if resource_group and account_name:
        try:
            completed = subprocess.run(
                [
                    _az_command_path(),
                    "cognitiveservices",
                    "account",
                    "deployment",
                    "list",
                    "--resource-group",
                    resource_group,
                    "--name",
                    account_name,
                    "--output",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=25,
                check=True,
            )
            for deployment in json.loads(completed.stdout or "[]"):
                props = deployment.get("properties") or {}
                capabilities = props.get("capabilities") or {}
                model = (props.get("model") or {}).get("name") or deployment.get("name")
                version = (props.get("model") or {}).get("version") or ""
                is_ready = props.get("provisioningState") == "Succeeded"
                supports_chat = capabilities.get("chatCompletion") == "true" or capabilities.get("responses") == "true"
                if not is_ready or not supports_chat:
                    continue
                metadata = _metadata_for_model("azure-openai", model)
                option = _model_option(
                    "azure-openai",
                    metadata,
                    deployment=deployment.get("name"),
                    version=version,
                    source="azure-deployment",
                )
                option["functional"] = True
                option["status_label"] = "Ready"
                option["is_default"] = deployment.get("name") == current_deployment
                options.append(option)
        except Exception:
            options = []

    if not options and current_deployment:
        metadata = _metadata_for_model("azure-openai", current_deployment)
        option = _model_option("azure-openai", metadata, deployment=current_deployment, source="backend-default")
        option["is_default"] = True
        options.append(option)

    return options

def _relocate_root_job_artifacts(job_id: str, job_output_dir: str) -> bool:
    """
    Backward-compat rescue:
    If main.py accidentally wrote metadata/clips into OUTPUT_DIR root (e.g. output/<jobid>_...),
    move them into output/<job_id>/ so the API can find and serve them.
    """
    try:
        os.makedirs(job_output_dir, exist_ok=True)
        root = OUTPUT_DIR
        pattern = os.path.join(root, f"{job_id}_*_metadata.json")
        meta_candidates = sorted(glob.glob(pattern), key=lambda p: os.path.getmtime(p), reverse=True)
        if not meta_candidates:
            return False

        # Move the newest metadata and its associated clips.
        metadata_path = meta_candidates[0]
        base_name = os.path.basename(metadata_path).replace("_metadata.json", "")

        # Move metadata
        dest_metadata = os.path.join(job_output_dir, os.path.basename(metadata_path))
        if os.path.abspath(metadata_path) != os.path.abspath(dest_metadata):
            shutil.move(metadata_path, dest_metadata)

        # Move any clips that match the same base_name into the job folder
        clip_pattern = os.path.join(root, f"{base_name}_clip_*.mp4")
        for clip_path in glob.glob(clip_pattern):
            dest_clip = os.path.join(job_output_dir, os.path.basename(clip_path))
            if os.path.abspath(clip_path) != os.path.abspath(dest_clip):
                shutil.move(clip_path, dest_clip)

        # Also move any temp_ clips that might remain
        temp_clip_pattern = os.path.join(root, f"temp_{base_name}_clip_*.mp4")
        for clip_path in glob.glob(temp_clip_pattern):
            dest_clip = os.path.join(job_output_dir, os.path.basename(clip_path))
            if os.path.abspath(clip_path) != os.path.abspath(dest_clip):
                shutil.move(clip_path, dest_clip)

        return True
    except Exception:
        return False

async def cleanup_jobs():
    """Background task to remove old jobs and files."""
    import time
    print("🧹 Cleanup task started.")
    while True:
        try:
            await asyncio.sleep(300) # Check every 5 minutes
            now = time.time()
            
            # Simple directory cleanup based on modification time
            # Check OUTPUT_DIR
            for job_id in os.listdir(OUTPUT_DIR):
                job_path = os.path.join(OUTPUT_DIR, job_id)
                if os.path.isdir(job_path):
                    if now - os.path.getmtime(job_path) > JOB_RETENTION_SECONDS:
                        print(f"🧹 Purging old job: {job_id}")
                        shutil.rmtree(job_path, ignore_errors=True)
                        if job_id in jobs:
                            del jobs[job_id]

            # Cleanup Uploads
            for filename in os.listdir(UPLOAD_DIR):
                file_path = os.path.join(UPLOAD_DIR, filename)
                try:
                    if now - os.path.getmtime(file_path) > JOB_RETENTION_SECONDS:
                         os.remove(file_path)
                except Exception: pass

        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")

async def process_queue():
    """Background worker to process jobs from the queue with concurrency limit."""
    print(f"🚀 Job Queue Worker started with {MAX_CONCURRENT_JOBS} concurrent slots.")
    while True:
        try:
            # Wait for a job
            job_id = await job_queue.get()
            
            # Acquire semaphore slot (waits if max jobs are running)
            await concurrency_semaphore.acquire()
            print(f"🔄 Acquired slot for job: {job_id}")

            # Process in background task to not block the loop (allowing other slots to fill)
            asyncio.create_task(run_job_wrapper(job_id))
            
        except Exception as e:
            print(f"❌ Queue dispatch error: {e}")
            await asyncio.sleep(1)

async def run_job_wrapper(job_id):
    """Wrapper to run job and release semaphore"""
    try:
        job = jobs.get(job_id)
        if job:
            await run_job(job_id, job)
    except Exception as e:
         print(f"❌ Job wrapper error {job_id}: {e}")
    finally:
        # Always release semaphore and mark queue task done
        concurrency_semaphore.release()
        job_queue.task_done()
        print(f"✅ Released slot for job: {job_id}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start worker and cleanup
    worker_task = asyncio.create_task(process_queue())
    cleanup_task = asyncio.create_task(cleanup_jobs())
    for name, task in (("job worker", worker_task), ("cleanup worker", cleanup_task)):
        task.add_done_callback(lambda done_task, task_name=name: _log_background_task_result(task_name, done_task))
    try:
        yield
    finally:
        for task in (worker_task, cleanup_task):
            task.cancel()


def _log_background_task_result(name: str, task: asyncio.Task):
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Background task crashed: {name}: {e}", flush=True)

app = FastAPI(lifespan=lifespan)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for serving videos
app.mount("/videos", StaticFiles(directory=OUTPUT_DIR), name="videos")

@app.get("/api/ai/defaults")
async def ai_defaults():
    """Return non-secret AI provider defaults configured on the backend."""
    provider = (os.environ.get("AI_PROVIDER") or ("gemini" if os.environ.get("GEMINI_API_KEY") else "")).strip()
    api_key = (os.environ.get("AI_API_KEY") or os.environ.get("GEMINI_API_KEY") or "").strip()
    return {
        "provider": provider,
        "model": (os.environ.get("AI_MODEL") or "").strip(),
        "baseUrl": (os.environ.get("AI_BASE_URL") or "").strip(),
        "azureEndpoint": (os.environ.get("AZURE_OPENAI_ENDPOINT") or "").strip(),
        "azureDeployment": (os.environ.get("AZURE_OPENAI_DEPLOYMENT") or "").strip(),
        "azureApiVersion": (os.environ.get("AZURE_OPENAI_API_VERSION") or "2024-10-21").strip(),
        "has_api_key": bool(api_key),
    }

@app.get("/api/ai/models")
async def ai_models(request: Request, provider: Optional[str] = None):
    """Return non-secret model/deployment options and ranking metadata for Settings."""
    selected_provider = (
        provider
        or request.headers.get("X-AI-Provider")
        or os.environ.get("AI_PROVIDER")
        or ("gemini" if os.environ.get("GEMINI_API_KEY") else "gemini")
    ).strip().lower()

    if selected_provider == "azure-openai":
        models = _azure_deployment_options()
        source = "azure-deployments"
    elif selected_provider == "custom-openai-compatible":
        current_model = request.headers.get("X-AI-Model") or os.environ.get("AI_MODEL") or ""
        models = [_model_option(selected_provider, _metadata_for_model(selected_provider, current_model), source="manual")] if current_model else []
        source = "manual"
    else:
        models = [_model_option(selected_provider, item, source="catalog") for item in MODEL_CATALOG.get(selected_provider, [])]
        source = "catalog"

    return {
        "provider": selected_provider,
        "source": source,
        "sort_options": MODEL_SORT_OPTIONS,
        "models": models,
        "notes": {
            "azure-openai": "Azure shows deployed chat-capable models only. Catalog models without deployment are not callable.",
            "gemini": "Gemini free tier depends on Google AI Studio quota and billing state.",
            "openai": "OpenAI API usage is billed by model tokens; account credits may offset charges.",
            "openrouter": "OpenRouter free models and limits change frequently; :free models are marked as free when routed by OpenRouter.",
            "nvidia-nim": "NVIDIA NIM availability and credits depend on the NVIDIA account/program.",
        }.get(selected_provider, "Provider availability depends on account and endpoint."),
    }

class ProcessRequest(BaseModel):
    url: str

def enqueue_output(out, job_id):
    """Reads output from a subprocess and appends it to jobs logs."""
    try:
        for line in iter(out.readline, b''):
            decoded_line = line.decode('utf-8').strip()
            if decoded_line:
                print(f"📝 [Job Output] {decoded_line}")
                if job_id in jobs:
                    jobs[job_id]['logs'].append(decoded_line)
    except Exception as e:
        print(f"Error reading output for job {job_id}: {e}")
    finally:
        out.close()

async def run_job(job_id, job_data):
    """Executes the subprocess for a specific job."""
    
    cmd = job_data['cmd']
    env = job_data['env']
    output_dir = job_data['output_dir']
    
    jobs[job_id]['status'] = 'processing'
    jobs[job_id]['logs'].append("Job started by worker.")
    print(f"🎬 [run_job] Executing command for {job_id}: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Merge stderr to stdout
            env=env,
            cwd=os.getcwd()
        )
        
        # We need to capture logs in a thread because Popen isn't async
        t_log = threading.Thread(target=enqueue_output, args=(process.stdout, job_id))
        t_log.daemon = True
        t_log.start()
        
        # Async wait for process with incremental updates
        start_wait = time.time()
        while process.poll() is None:
            await asyncio.sleep(2)
            
            # Check for partial results every 2 seconds
            # Look for metadata file
            try:
                json_files = glob.glob(os.path.join(output_dir, "*_metadata.json"))
                if json_files:
                    target_json = json_files[0]
                    # Read metadata (it might be being written to, so simple try/except or just read)
                    # Use a lock or just robust read? json.load might fail if file is partial.
                    # Usually main.py writes it once at start (based on my review).
                    if os.path.getsize(target_json) > 0:
                        with open(target_json, 'r') as f:
                            data = json.load(f)
                            
                        base_name = os.path.basename(target_json).replace('_metadata.json', '')
                        clips = data.get('shorts', [])
                        cost_analysis = data.get('cost_analysis')
                        
                        # Check which clips actually exist on disk
                        ready_clips = []
                        for i, clip in enumerate(clips):
                             clip_filename = f"{base_name}_clip_{i+1}.mp4"
                             clip_path = os.path.join(output_dir, clip_filename)
                             if os.path.exists(clip_path) and os.path.getsize(clip_path) > 0:
                                 # Checking if file is growing? For now assume if it exists and main.py moves it there, it's done.
                                 # main.py writes to temp_... then moves to final name. So presence means ready!
                                 clip['video_url'] = f"/videos/{job_id}/{clip_filename}"
                                 ready_clips.append(clip)
                        
                        if ready_clips:
                             jobs[job_id]['result'] = {'clips': ready_clips, 'cost_analysis': cost_analysis}
            except Exception as e:
                # Ignore read errors during processing
                pass

        returncode = process.returncode
        
        if returncode == 0:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['logs'].append("Process finished successfully.")
            
            # Find result JSON
            json_files = glob.glob(os.path.join(output_dir, "*_metadata.json"))
            if not json_files:
                # Backward-compat rescue if outputs were written to OUTPUT_DIR root
                if _relocate_root_job_artifacts(job_id, output_dir):
                    json_files = glob.glob(os.path.join(output_dir, "*_metadata.json"))
            if json_files:
                target_json = json_files[0] 
                with open(target_json, 'r') as f:
                    data = json.load(f)
                
                # Enhance result with video URLs
                base_name = os.path.basename(target_json).replace('_metadata.json', '')
                clips = data.get('shorts', [])
                cost_analysis = data.get('cost_analysis')

                for i, clip in enumerate(clips):
                     clip_filename = f"{base_name}_clip_{i+1}.mp4"
                     clip['video_url'] = f"/videos/{job_id}/{clip_filename}"
                
                jobs[job_id]['result'] = {'clips': clips, 'cost_analysis': cost_analysis}
            else:
                 jobs[job_id]['status'] = 'failed'
                 jobs[job_id]['logs'].append("No metadata file generated.")
        else:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['logs'].append(f"Process failed with exit code {returncode}")
            
    except Exception as e:
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['logs'].append(f"Execution error: {str(e)}")

@app.post("/api/process")
async def process_endpoint(
    request: Request,
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None)
):
    ai_env = build_ai_env(request)

    # Handle JSON body manually for URL payload
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        url = body.get("url")
    
    if not url and not file:
        raise HTTPException(status_code=400, detail="Must provide URL or File")

    job_id = str(uuid.uuid4())
    job_output_dir = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(job_output_dir, exist_ok=True)
    
    # Prepare Command
    cmd = ["python", "-u", "main.py"] # -u for unbuffered
    env = os.environ.copy()
    env.update(ai_env)
    env.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    env.setdefault("OMP_NUM_THREADS", "1")
    
    if url:
        cmd.extend(["-u", url])
    else:
        # Save uploaded file with size limit check
        input_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
        
        # Read file in chunks to check size
        size = 0
        limit_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        
        with open(input_path, "wb") as buffer:
            while content := await file.read(1024 * 1024): # Read 1MB chunks
                size += len(content)
                if size > limit_bytes:
                    os.remove(input_path)
                    shutil.rmtree(job_output_dir)
                    raise HTTPException(status_code=413, detail=f"File too large. Max size {MAX_FILE_SIZE_MB}MB")
                buffer.write(content)
                
        cmd.extend(["-i", input_path])

    cmd.extend(["-o", job_output_dir])

    # Enqueue Job
    jobs[job_id] = {
        'status': 'queued',
        'logs': [f"Job {job_id} queued."],
        'cmd': cmd,
        'env': env,
        'output_dir': job_output_dir
    }
    
    await job_queue.put(job_id)
    
    return {"job_id": job_id, "status": "queued"}

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    return {
        "status": job['status'],
        "logs": job['logs'],
        "result": job.get('result')
    }

from editor import VideoEditor
from subtitles import generate_srt, burn_subtitles
from hooks import add_hook_to_video

class EditRequest(BaseModel):
    job_id: str
    clip_index: int
    api_key: Optional[str] = None
    input_filename: Optional[str] = None

@app.post("/api/edit")
async def edit_clip(
    req: EditRequest,
    request: Request,
    x_gemini_key: Optional[str] = Header(None, alias="X-Gemini-Key")
):
    # Determine API Key
    ai_env = build_ai_env(request, require_key=False)
    if req.api_key and not ai_env.get("AI_API_KEY"):
        ai_env["AI_PROVIDER"] = "gemini"
        ai_env["AI_API_KEY"] = req.api_key
        ai_env["GEMINI_API_KEY"] = req.api_key
    final_api_key = req.api_key or x_gemini_key or ai_env.get("GEMINI_API_KEY") or ai_env.get("AI_API_KEY")
    
    if (ai_env.get("AI_PROVIDER") or "gemini").lower() != "gemini":
        raise HTTPException(status_code=400, detail="Auto Edit currently requires Gemini because it uses Gemini video upload.")

    if not final_api_key:
        raise HTTPException(status_code=400, detail="Missing Gemini API key for Auto Edit.")

    if req.job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[req.job_id]
    if 'result' not in job or 'clips' not in job['result']:
        raise HTTPException(status_code=400, detail="Job result not available")
        
    try:
        # Resolve Input Path: Prefer explict input_filename from frontend (chaining edits)
        if req.input_filename:
            # Security: Ensure just a filename, no paths
            safe_name = os.path.basename(req.input_filename)
            input_path = os.path.join(OUTPUT_DIR, req.job_id, safe_name)
            filename = safe_name
        else:
            # Fallback to original clip
            clip = job['result']['clips'][req.clip_index]
            filename = clip['video_url'].split('/')[-1]
            input_path = os.path.join(OUTPUT_DIR, req.job_id, filename)
        
        if not os.path.exists(input_path):
             raise HTTPException(status_code=404, detail=f"Video file not found: {input_path}")

        # Define output path for edited video
        edited_filename = f"edited_{filename}"
        output_path = os.path.join(OUTPUT_DIR, req.job_id, edited_filename)
        
        # Run editing in a thread to avoid blocking main loop
        # Since VideoEditor uses blocking calls (subprocess, API wait)
        def run_edit():
            editor = VideoEditor(api_key=final_api_key)
            
            # SAFE FILE RENAMING STRATEGY (Avoid UnicodeEncodeError in Docker)
            # Create a safe ASCII filename in the same directory
            safe_filename = f"temp_input_{req.job_id}.mp4"
            safe_input_path = os.path.join(OUTPUT_DIR, req.job_id, safe_filename)
            
            # Copy original file to safe path
            # (Copy is safer than rename if something crashes, we keep original)
            shutil.copy(input_path, safe_input_path)
            
            try:
                # 1. Upload (using safe path)
                vid_file = editor.upload_video(safe_input_path)
                
                # 2. Get duration
                import cv2
                cap = cv2.VideoCapture(safe_input_path)
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                duration = frame_count / fps if fps else 0
                cap.release()
                
                # Load transcript from metadata
                transcript = None
                try:
                    meta_files = glob.glob(os.path.join(OUTPUT_DIR, req.job_id, "*_metadata.json"))
                    if meta_files:
                        with open(meta_files[0], 'r') as f:
                            data = json.load(f)
                            transcript = data.get('transcript')
                except Exception as e:
                    print(f"⚠️ Could not load transcript for editing context: {e}")

                # 3. Get Plan (Filter String)
                filter_data = editor.get_ffmpeg_filter(vid_file, duration, fps=fps, width=width, height=height, transcript=transcript)
                
                # 4. Apply
                # Use safe output name first
                safe_output_path = os.path.join(OUTPUT_DIR, req.job_id, f"temp_output_{req.job_id}.mp4")
                editor.apply_edits(safe_input_path, safe_output_path, filter_data)
                
                # Move result to final destination (rename works even if dest name has unicode if filesystem supports it, 
                # but python might still struggle if locale is broken? No, os.rename usually handles it better than subprocess args)
                # Actually, output_path is defined above: f"edited_{filename}"
                # If filename has unicode, output_path has unicode.
                # Let's hope shutil.move / os.rename works.
                if os.path.exists(safe_output_path):
                    shutil.move(safe_output_path, output_path)
                
                return filter_data
            finally:
                # Cleanup temp safe input
                if os.path.exists(safe_input_path):
                    os.remove(safe_input_path)

        # Run in thread pool
        loop = asyncio.get_event_loop()
        plan = await loop.run_in_executor(None, run_edit)
        
        # Update clip URL in the job result? 
        # Or return new URL and let frontend handle it?
        # Updating job result allows persistence if page refreshes.
        
        new_video_url = f"/videos/{req.job_id}/{edited_filename}"
        
        # Start a new "edited" clip entry or just update the current one?
        # Let's update the current one's video_url but keep backup?
        # Or return the new URL to the frontend to display.
        
        return {
            "success": True, 
            "new_video_url": new_video_url,
            "edit_plan": plan
        }

    except Exception as e:
        print(f"❌ Edit Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class SubtitleRequest(BaseModel):
    job_id: str
    clip_index: int
    position: str = "bottom" # top, middle, bottom
    font_size: int = 16
    font_name: str = "Verdana"
    font_color: str = "#FFFFFF"
    border_color: str = "#000000"
    border_width: int = 2
    bg_color: str = "#000000"
    bg_opacity: float = 0.0
    input_filename: Optional[str] = None


@app.get("/api/clip/{job_id}/{clip_index}/transcript")
async def get_clip_transcript(job_id: str, clip_index: int):
    """Return word-level captions for a specific clip, formatted for Remotion."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    output_dir = os.path.join(OUTPUT_DIR, job_id)
    json_files = glob.glob(os.path.join(output_dir, "*_metadata.json"))

    if not json_files:
        raise HTTPException(status_code=404, detail="Metadata not found")

    with open(json_files[0], 'r') as f:
        data = json.load(f)

    transcript = data.get('transcript')
    if not transcript:
        raise HTTPException(status_code=400, detail="Transcript not found in metadata")

    clips = data.get('shorts', [])
    if clip_index >= len(clips):
        raise HTTPException(status_code=404, detail="Clip not found")

    clip_data = clips[clip_index]
    clip_start = clip_data.get('start', 0)
    clip_end = clip_data.get('end', 0)

    # Extract words within clip range and convert to CaptionWord format
    captions = []
    for segment in transcript.get('segments', []):
        for word_info in segment.get('words', []):
            if word_info['end'] > clip_start and word_info['start'] < clip_end:
                captions.append({
                    "text": word_info.get('word', '').strip(),
                    "startMs": int((max(0, word_info['start'] - clip_start)) * 1000),
                    "endMs": int((max(0, word_info['end'] - clip_start)) * 1000),
                })

    duration_sec = clip_end - clip_start

    return {
        "captions": captions,
        "durationSec": duration_sec,
        "language": transcript.get('language', 'en'),
    }


# --- Remotion Render Proxy ---
RENDER_SERVICE_URL = os.getenv("RENDER_SERVICE_URL", "http://localhost:3100")

@app.post("/api/render")
async def proxy_render(request: Request):
    """Proxy render requests to the Node.js Remotion render service."""
    import httpx
    body = await request.json()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{RENDER_SERVICE_URL}/render", json=body)
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Render service unavailable: {e}")

@app.get("/api/render/{render_id}")
async def proxy_render_status(render_id: str):
    """Proxy render status polling to the Node.js Remotion render service."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{RENDER_SERVICE_URL}/render/{render_id}")
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Render service unavailable: {e}")


class EffectsGenerateRequest(BaseModel):
    job_id: str
    clip_index: int
    input_filename: Optional[str] = None

@app.post("/api/effects/generate")
async def generate_effects_config(
    req: EffectsGenerateRequest,
    request: Request,
    x_gemini_key: Optional[str] = Header(None, alias="X-Gemini-Key")
):
    """Generate structured EffectsConfig JSON for Remotion rendering via Gemini AI."""
    ai_env = build_ai_env(request)
    final_api_key = x_gemini_key or ai_env.get("GEMINI_API_KEY") or ai_env.get("AI_API_KEY")

    if (ai_env.get("AI_PROVIDER") or "gemini").lower() != "gemini":
        raise HTTPException(status_code=400, detail="AI effects currently require Gemini because they use Gemini video upload.")

    if req.job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[req.job_id]
    if 'result' not in job or 'clips' not in job['result']:
        raise HTTPException(status_code=400, detail="Job result not available")

    try:
        # Resolve input path
        if req.input_filename:
            safe_name = os.path.basename(req.input_filename)
            input_path = os.path.join(OUTPUT_DIR, req.job_id, safe_name)
        else:
            clip = job['result']['clips'][req.clip_index]
            filename = clip['video_url'].split('/')[-1]
            input_path = os.path.join(OUTPUT_DIR, req.job_id, filename)

        if not os.path.exists(input_path):
            raise HTTPException(status_code=404, detail=f"Video file not found: {input_path}")

        def run_effects_generation():
            editor = VideoEditor(api_key=final_api_key)

            # Create safe ASCII filename to avoid encoding issues
            safe_filename = f"temp_effects_{req.job_id}.mp4"
            safe_input_path = os.path.join(OUTPUT_DIR, req.job_id, safe_filename)
            shutil.copy(input_path, safe_input_path)

            try:
                # Upload video to Gemini
                vid_file = editor.upload_video(safe_input_path)

                # Get video metadata via ffprobe
                probe_cmd = [
                    'ffprobe', '-v', 'error',
                    '-select_streams', 'v:0',
                    '-show_entries', 'stream=width,height,r_frame_rate,duration',
                    '-show_entries', 'format=duration',
                    '-of', 'json',
                    safe_input_path
                ]
                probe_result = subprocess.check_output(probe_cmd).decode().strip()
                probe_data = json.loads(probe_result)

                stream = probe_data.get('streams', [{}])[0]
                width = int(stream.get('width', 1080))
                height = int(stream.get('height', 1920))

                # Parse fps from r_frame_rate (e.g. "30/1")
                r_frame_rate = stream.get('r_frame_rate', '30/1')
                num, den = r_frame_rate.split('/')
                fps = round(int(num) / int(den), 2)

                # Get duration from stream or format
                duration = float(stream.get('duration', 0))
                if duration == 0:
                    duration = float(probe_data.get('format', {}).get('duration', 0))

                # Load transcript from metadata
                transcript = None
                try:
                    meta_files = glob.glob(os.path.join(OUTPUT_DIR, req.job_id, "*_metadata.json"))
                    if meta_files:
                        with open(meta_files[0], 'r') as f:
                            data = json.load(f)
                            transcript = data.get('transcript')
                except Exception as e:
                    print(f"⚠️ Could not load transcript for effects config: {e}")

                # Generate effects config
                effects_config = editor.get_effects_config(
                    vid_file, duration, fps=fps, width=width, height=height, transcript=transcript
                )

                return effects_config
            finally:
                if os.path.exists(safe_input_path):
                    os.remove(safe_input_path)

        loop = asyncio.get_event_loop()
        effects_config = await loop.run_in_executor(None, run_effects_generation)

        if effects_config is None:
            raise HTTPException(status_code=500, detail="Failed to generate effects config from Gemini")

        return {"effects": effects_config}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Effects Generation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/subtitle")
async def add_subtitles(req: SubtitleRequest):
    if req.job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Reload job data from disk just in case metadata was updated
    job = jobs[req.job_id]
    
    # We need to access metadata.json to get the transcript
    output_dir = os.path.join(OUTPUT_DIR, req.job_id)
    json_files = glob.glob(os.path.join(output_dir, "*_metadata.json"))
    
    if not json_files:
        raise HTTPException(status_code=404, detail="Metadata not found")
        
    with open(json_files[0], 'r') as f:
        data = json.load(f)
        
    transcript = data.get('transcript')
    if not transcript:
        raise HTTPException(status_code=400, detail="Transcript not found in metadata. Please process a new video.")
        
    clips = data.get('shorts', [])
    if req.clip_index >= len(clips):
        raise HTTPException(status_code=404, detail="Clip not found")
        
    clip_data = clips[req.clip_index]
    
    # Video Path
    if req.input_filename:
        # Use chained file
        filename = os.path.basename(req.input_filename)
    else:
        # Fallback to standard naming
        filename = clip_data.get('video_url', '').split('/')[-1]
        if not filename:
             base_name = os.path.basename(json_files[0]).replace('_metadata.json', '')
             filename = f"{base_name}_clip_{req.clip_index+1}.mp4"
         
    input_path = os.path.join(output_dir, filename)
    if not os.path.exists(input_path):
        # Try looking for edited version if url implied it?
        # Just fail if not found.
        raise HTTPException(status_code=404, detail=f"Video file not found: {input_path}")
        
    # Define outputs
    srt_filename = f"subs_{req.clip_index}_{int(time.time())}.srt"
    srt_path = os.path.join(output_dir, srt_filename)
    
    # Output video
    # We create a new file "subtitled_..."
    output_filename = f"subtitled_{filename}"
    output_path = os.path.join(output_dir, output_filename)
    
    try:
        # 1. Generate SRT
        success = generate_srt(transcript, clip_data['start'], clip_data['end'], srt_path)

        if not success:
             raise HTTPException(status_code=400, detail="No words found for this clip range.")

        # 2. Burn Subtitles
        # Run in thread pool
        def run_burn():
             burn_subtitles(input_path, srt_path, output_path,
                           alignment=req.position, fontsize=req.font_size,
                           font_name=req.font_name, font_color=req.font_color,
                           border_color=req.border_color, border_width=req.border_width,
                           bg_color=req.bg_color, bg_opacity=req.bg_opacity)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run_burn)
        
    except Exception as e:
        print(f"❌ Subtitle Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    # 3. Update Result and Metadata
    # Update InMemory Jobs
    if req.clip_index < len(job['result']['clips']):
         job['result']['clips'][req.clip_index]['video_url'] = f"/videos/{req.job_id}/{output_filename}"
    
    # Update Metadata on Disk (Persistence)
    try:
        if req.clip_index < len(clips):
            clips[req.clip_index]['video_url'] = f"/videos/{req.job_id}/{output_filename}"
            # Update the main data structure
            data['shorts'] = clips
            
            # Write back
            with open(json_files[0], 'w') as f:
                json.dump(data, f, indent=4)
                print(f"✅ Metadata updated with subtitled video for clip {req.clip_index}")
    except Exception as e:
        print(f"⚠️ Failed to update metadata.json: {e}")
        # Non-critical, but good for persistence

    return {
        "success": True,
        "new_video_url": f"/videos/{req.job_id}/{output_filename}"
    }

class HookRequest(BaseModel):
    job_id: str
    clip_index: int
    text: str
    input_filename: Optional[str] = None
    position: Optional[str] = "top" # top, center, bottom
    size: Optional[str] = "M" # S, M, L

@app.post("/api/hook")
async def add_hook(req: HookRequest):
    if req.job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[req.job_id]
    output_dir = os.path.join(OUTPUT_DIR, req.job_id)
    json_files = glob.glob(os.path.join(output_dir, "*_metadata.json"))
    
    if not json_files:
        raise HTTPException(status_code=404, detail="Metadata not found")
        
    with open(json_files[0], 'r') as f:
        data = json.load(f)
        
    clips = data.get('shorts', [])
    if req.clip_index >= len(clips):
        raise HTTPException(status_code=404, detail="Clip not found")
        
    clip_data = clips[req.clip_index]
    
    # Video Path
    if req.input_filename:
        filename = os.path.basename(req.input_filename)
    else:
        filename = clip_data.get('video_url', '').split('/')[-1]
        if not filename:
             base_name = os.path.basename(json_files[0]).replace('_metadata.json', '')
             filename = f"{base_name}_clip_{req.clip_index+1}.mp4"
         
    input_path = os.path.join(output_dir, filename)
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail=f"Video file not found: {input_path}")
        
    # Output video
    output_filename = f"hook_{filename}"
    output_path = os.path.join(output_dir, output_filename)
    
    # Map Size to Scale
    size_map = {"S": 0.8, "M": 1.0, "L": 1.3}
    font_scale = size_map.get(req.size, 1.0)
    
    try:
        # Run in thread pool
        def run_hook():
             add_hook_to_video(input_path, req.text, output_path, position=req.position, font_scale=font_scale)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run_hook)
        
    except Exception as e:
        print(f"❌ Hook Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    # Update Persistence (Same logic as subtitles)
    # Update InMemory Jobs
    if req.clip_index < len(job['result']['clips']):
         job['result']['clips'][req.clip_index]['video_url'] = f"/videos/{req.job_id}/{output_filename}"
    
    # Update Metadata on Disk
    try:
        if req.clip_index < len(clips):
            clips[req.clip_index]['video_url'] = f"/videos/{req.job_id}/{output_filename}"
            data['shorts'] = clips
            with open(json_files[0], 'w') as f:
                json.dump(data, f, indent=4)
                print(f"✅ Metadata updated with hook video for clip {req.clip_index}")
    except Exception as e:
        print(f"⚠️ Failed to update metadata.json: {e}")

    return {
        "success": True,
        "new_video_url": f"/videos/{req.job_id}/{output_filename}"
    }

class SocialPostRequest(BaseModel):
    job_id: str
    clip_index: int
    api_key: str
    user_id: str
    platforms: List[str] # ["tiktok", "instagram", "youtube"]
    # Optional overrides if frontend wants to edit them
    title: Optional[str] = None
    description: Optional[str] = None
    scheduled_date: Optional[str] = None # ISO-8601 string
    timezone: Optional[str] = "UTC"

import httpx

@app.post("/api/social/post")
async def post_to_socials(req: SocialPostRequest):
    if req.job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[req.job_id]
    if 'result' not in job or 'clips' not in job['result']:
        raise HTTPException(status_code=400, detail="Job result not available")
        
    try:
        clip = job['result']['clips'][req.clip_index]
        # Video URL is relative /videos/..., we need absolute file path
        # clip['video_url'] is like "/videos/{job_id}/{filename}"
        # We constructed it as: f"/videos/{job_id}/{clip_filename}"
        # And file is at f"{OUTPUT_DIR}/{job_id}/{clip_filename}"
        
        filename = clip['video_url'].split('/')[-1]
        file_path = os.path.join(OUTPUT_DIR, req.job_id, filename)
        
        if not os.path.exists(file_path):
             raise HTTPException(status_code=404, detail=f"Video file not found: {file_path}")

        # Construct parameters for Upload-Post API
        # Fallbacks
        final_title = req.title or clip.get('title', 'Viral Short')
        final_description = req.description or clip.get('video_description_for_instagram') or clip.get('video_description_for_tiktok') or "Check this out!"
        
        # Prepare form data
        url = "https://api.upload-post.com/api/upload"
        headers = {
            "Authorization": f"Apikey {req.api_key}"
        }
        
        # Prepare data as dict (httpx handles lists for multiple values)
        data_payload = {
            "user": req.user_id,
            "title": final_title,
            "platform[]": req.platforms, # Pass list directly
            "async_upload": "true"  # Enable async upload
        }

        # Add scheduling if present
        if req.scheduled_date:
            data_payload["scheduled_date"] = req.scheduled_date
            if req.timezone:
                data_payload["timezone"] = req.timezone
        
        # Add Platform specifics
        if "tiktok" in req.platforms:
             data_payload["tiktok_title"] = final_description
             
        if "instagram" in req.platforms:
             data_payload["instagram_title"] = final_description
             data_payload["media_type"] = "REELS"

        if "youtube" in req.platforms:
             yt_title = req.title or clip.get('video_title_for_youtube_short', final_title)
             data_payload["youtube_title"] = yt_title
             data_payload["youtube_description"] = final_description
             data_payload["privacyStatus"] = "public"

        # Send File
        # httpx AsyncClient requires async file reading or bytes. 
        # Since we have MAX_FILE_SIZE_MB, reading into memory is safe-ish.
        with open(file_path, "rb") as f:
            file_content = f.read()
            
        files = {
            "video": (filename, file_content, "video/mp4")
        }

        # Switch to synchronous Client to avoid "sync request with AsyncClient" error with multipart/files
        with httpx.Client(timeout=120.0) as client:
            print(f"📡 Sending to Upload-Post for platforms: {req.platforms}")
            response = client.post(url, headers=headers, data=data_payload, files=files)
            
        if response.status_code not in [200, 201, 202]: # Added 201
             print(f"❌ Upload-Post Error: {response.text}")
             raise HTTPException(status_code=response.status_code, detail=f"Vendor API Error: {response.text}")

        return response.json()

    except Exception as e:
        print(f"❌ Social Post Exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/social/user")
async def get_social_user(api_key: str = Header(..., alias="X-Upload-Post-Key")):
    """Proxy to fetch user ID from Upload-Post"""
    if not api_key:
         raise HTTPException(status_code=400, detail="Missing X-Upload-Post-Key header")
         
    url = "https://api.upload-post.com/api/uploadposts/users"
    print(f"🔍 Fetching User ID from: {url}")
    headers = {"Authorization": f"Apikey {api_key}"}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                print(f"❌ Upload-Post User Fetch Error: {resp.text}")
                raise HTTPException(status_code=resp.status_code, detail=f"Failed to fetch user: {resp.text}")
            
            data = resp.json()
            print(f"🔍 Upload-Post User Response: {data}")
            
            user_id = None
            # The structure is {'success': True, 'profiles': [{'username': '...'}, ...]}
            profiles_list = []
            if isinstance(data, dict):
                 raw_profiles = data.get('profiles', [])
                 if isinstance(raw_profiles, list):
                     for p in raw_profiles:
                         username = p.get('username')
                         if username:
                             # Determine connected platforms
                             socials = p.get('social_accounts', {})
                             connected = []
                             # Check typical platforms
                             for platform in ['tiktok', 'instagram', 'youtube']:
                                 account_info = socials.get(platform)
                                 # If it's a dict and typically has data, or just not empty string
                                 if isinstance(account_info, dict):
                                     connected.append(platform)
                             
                             profiles_list.append({
                                 "username": username,
                                 "connected": connected
                             })
            
            if not profiles_list:
                # Fallback if no profiles found
                return {"profiles": [], "error": "No profiles found"}
                
            return {"profiles": profiles_list}
            
            
        except Exception as e:
             raise HTTPException(status_code=500, detail=str(e))

