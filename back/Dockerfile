FROM python:3.11-slim

# Do not write .pyc files and make stdout/stderr unbuffered
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies commonly needed for OpenCV/Media processing and build tools
RUN apt-get update \
		&& apt-get install -y --no-install-recommends \
			 gcc \
			 ffmpeg \
			 libgl1 \
			 libglib2.0-0 \
			 libsm6 \
			 libxrender1 \
			 libxext6 \
			 git \
		&& rm -rf /var/lib/apt/lists/*

# Copy optional requirements file first to leverage Docker layer caching
COPY ../requirements.txt ./requirements.txt

# Install python dependencies. If requirements.txt does not exist, install a sensible default set.
RUN if [ -f ./requirements.txt ]; then \
			pip install --no-cache-dir -r ./requirements.txt; \
		else \
			pip install --no-cache-dir fastapi uvicorn[standard] numpy opencv-python-headless pydantic; \
		fi

# Copy the rest of the project into the image
COPY .. /app

# Expose the FastAPI default port
EXPOSE 8000

# Create a non-root user for running the app
RUN useradd -m appuser || true
USER appuser

# Default command (development friendly). In production remove --reload and consider an ASGI server/process manager.
CMD ["uvicorn", "back.app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"]

