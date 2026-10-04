# Image cho dich vu "ingest" (docker-compose.yml): chay embed_chunks.py / search_chunks.py.
# KHONG copy code hay du lieu vao image — docker-compose.yml gan (mount) ./ vao /app luc chay,
# vi du lieu va script doi thuong xuyen (copy thi moi lan doi phai build lai; data/raw/ rat nang).
FROM python:3.12-slim

WORKDIR /app

COPY scripts/requirements-ingest.txt /tmp/requirements-ingest.txt
RUN pip install --no-cache-dir -r /tmp/requirements-ingest.txt

# Khong co CMD/ENTRYPOINT co dinh: docker-compose.yml goi lenh cu the qua
# "docker compose run --rm ingest python scripts/<ten script>.py ..."
