# PowerShell script to run all AI-related tests and benchmarks
# usage: .\Backend\scripts\run_ai_tests.ps1

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🚀 STARTING COMPREHENSIVE AI TEST SUITE (Gemini/Perplexity)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$env:PYTHONPATH = (Get-Item .).FullName

# 1. Run Unit Tests
Write-Host "`n🧪 [UNIT TESTS] Running GeminiClient/PerplexityClient unit tests..." -ForegroundColor Yellow
python -m unittest Backend/lead_magnets/tests/test_ai_client.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Unit tests failed. Aborting." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Unit tests passed." -ForegroundColor Green

# 2. Run Integration Tests
Write-Host "`n🧪 [INTEGRATION TESTS] Running real-world AI generation scenarios..." -ForegroundColor Yellow
python -m unittest Backend/lead_magnets/tests/test_ai_integration.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Integration tests failed. Aborting." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Integration tests passed." -ForegroundColor Green

# 3. Run Performance Benchmarks
Write-Host "`n🧪 [PERFORMANCE BENCHMARKS] Measuring AI response times..." -ForegroundColor Yellow
python Backend/scripts/benchmark_ai.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Performance benchmarks failed. Aborting." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Performance benchmarks completed." -ForegroundColor Green

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "✅ ALL TESTS PASSED. DEPLOYMENT PROTOCOL SUCCESSFUL." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
