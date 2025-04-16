# Video Processing API

## System Requirements

- Python 3.10 or higher
- FFmpeg (required for video processing)

## Installation

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Linux/Mac
# or
.venv\Scripts\activate  # On Windows
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

1. Start the server:

```bash
uvicorn main:app --reload
```

2. API Endpoint:

- **POST /process-videos**
    - Input:
        - `main_video`: Main video (file)
        - `secondary_videos`: List of secondary videos (multiple files)
    - Output: Zip file containing processed videos

## Example usage with curl

```bash
curl -X POST "http://localhost:8000/process-videos" \
  -H "accept: application/zip" \
  -H "Content-Type: multipart/form-data" \
  -F "main_video=@main.mp4" \
  -F "secondary_videos=@secondary1.mp4" \
  -F "secondary_videos=@secondary2.mp4" \
  --output processed_videos.zip
```

## Notes

- The API will automatically delete temporary files after processing
- Output video size will be automatically adjusted
- Output video will have a resolution of 720x1280 