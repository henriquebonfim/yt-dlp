.PHONY: build run clean logs shell

IMAGE_NAME := yt-dlp-downloader
DOWNLOADS_DIR := $(PWD)/downloads

build:
	docker build -t $(IMAGE_NAME) .

run: build
	@mkdir -p $(DOWNLOADS_DIR)
	@touch queue.md log.json failed.md
	docker run --rm \
		--user $(shell id -u):$(shell id -g) \
		-v $(DOWNLOADS_DIR):/app/downloads \
		-v $(PWD)/queue.md:/app/queue.md \
		-v $(PWD)/log.json:/app/log.json \
		-v $(PWD)/failed.md:/app/failed.md \
		$(IMAGE_NAME)

clean:
	docker rmi $(IMAGE_NAME) 2>/dev/null || true
