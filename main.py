import logging
import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from service import process_multiple_videos, create_zip_file, cleanup_files

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories for uploads and processed files
UPLOAD_DIR = "uploads"
PROCESSED_DIR = "processed"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
MAX_CONCURRENT_WORKERS = 4

def file_cleanup(*files):
    """Clean up files after streaming"""
    for file_path in files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Đã xóa file: {file_path}")
            except Exception as e:
                logger.error(f"Lỗi khi xóa file {file_path}: {str(e)}")


@app.post("/process-videos")
async def process_videos_endpoint(
        background_tasks: BackgroundTasks,
        main_video: UploadFile = File(...),
        secondary_videos: list[UploadFile] = File(...)
):
    # Generate unique filenames
    main_filename = f"{uuid.uuid4()}_{main_video.filename}"
    main_path = os.path.join(UPLOAD_DIR, main_filename)

    # Save main video
    try:
        with open(main_path, "wb") as main_file:
            main_file.write(await main_video.read())
    except Exception as e:
        logger.error(f"Lỗi khi lưu file main video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    # Save secondary videos
    secondary_paths = []
    try:
        for secondary_video in secondary_videos:
            secondary_filename = f"{uuid.uuid4()}_{secondary_video.filename}"
            secondary_path = os.path.join(UPLOAD_DIR, secondary_filename)
            with open(secondary_path, "wb") as secondary_file:
                secondary_file.write(await secondary_video.read())
            secondary_paths.append(secondary_path)
    except Exception as e:
        cleanup_files(main_path, secondary_paths)
        logger.error(f"Lỗi khi lưu file secondary video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    # Generate output paths
    zip_filename = f"{uuid.uuid4()}_outputs.zip"
    zip_path = os.path.join(PROCESSED_DIR, zip_filename)

    try:
        # Process videos
        output_files = process_multiple_videos(main_path, secondary_paths, PROCESSED_DIR,max_workers=MAX_CONCURRENT_WORKERS)

        if not output_files:
            raise HTTPException(status_code=500, detail="Không có video nào được xử lý thành công")

        # Create zip file
        create_zip_file(output_files, zip_path)
        logger.info(f"Đã tạo file zip: {zip_path}")

        # Clean up uploaded files
        cleanup_files(main_path, secondary_paths)

        # Create streaming response
        def cleanup():
            cleanup_files(output_files, zip_path)
            logger.info("Đã xóa các file output và zip")

        def file_stream():
            try:
                with open(zip_path, "rb") as f:
                    while chunk := f.read(8192):
                        yield chunk
            finally:
                cleanup()

        # Add cleanup task
        background_tasks.add_task(cleanup)

        # Return streaming response
        return StreamingResponse(
            file_stream(),
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=processed_videos.zip",
                "Content-Length": str(os.path.getsize(zip_path))
            }
        )
    except Exception as e:
        # Clean up in case of error
        cleanup_files(main_path, secondary_paths, zip_path)
        logger.error(f"Lỗi xử lý video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
