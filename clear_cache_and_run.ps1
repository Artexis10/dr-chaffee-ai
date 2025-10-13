# Clear Python cache and run ingestion
Write-Host "🧹 Clearing Python cache..." -ForegroundColor Yellow

# Remove all __pycache__ directories
Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Write-Host "✅ Cleared __pycache__ directories" -ForegroundColor Green

# Remove all .pyc files
Get-ChildItem -Path . -Recurse -File -Filter "*.pyc" | Remove-Item -Force
Write-Host "✅ Cleared .pyc files" -ForegroundColor Green

Write-Host ""
Write-Host "🚀 Starting ingestion with fresh code..." -ForegroundColor Cyan
Write-Host ""

# Run ingestion
python backend/scripts/ingest_youtube.py --source yt-dlp --limit 5 --limit-unprocessed
