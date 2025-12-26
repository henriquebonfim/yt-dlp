# YouTube CLI Downloader

A minimal YouTube queue downloader that runs in Docker.

![image](https://github.com/user-attachments/assets/bd8e4569-ffd9-4d52-960f-f564e3c6d9fe)

## Features

- Reads URLs from `queue.md` (plain or markdown links)
- Downloads the best available video/audio combination
- Records failures after max retries into `failed.md`
- Appends run history to `log.json`
- Runs in Docker with downloads saved to host

## Quick Start

### Using Make (Recommended)

```bash
# Add YouTube URLs to queue.md
echo "https://www.youtube.com/watch?v=VIDEO_ID" >> queue.md

# Build and run
make run
```

### Using Docker Compose

```bash
docker compose run --rm yt-dlp
```

### Using Docker directly

```bash
docker build -t yt-dlp-downloader .
docker run --rm \
  --user $(id -u):$(id -g) \
  -v ./downloads:/app/downloads \
  -v ./queue.md:/app/queue.md \
  -v $(PWD)/log.json:/app/log.json \
  -v $(PWD)/failed.md:/app/failed.md \
  yt-dlp-downloader
```

## Make Commands

| Command | Description |
|---------|-------------|
| `make build` | Build the Docker image |
| `make run` | Build and run the downloader |
| `make shell` | Open a bash shell in the container |
| `make clean` | Remove the Docker image |

## Files

- `queue.md` - Add YouTube URLs here (one per line)
- `downloads/` - Downloaded videos are saved here
- `log.json` - Download history log
- `failed.md` - URLs that failed after retries

## Requirements

- Docker
