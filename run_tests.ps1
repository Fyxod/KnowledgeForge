<#
.SYNOPSIS
    Test runner for the PRISM backend.

.DESCRIPTION
    Run tests using one of the following commands:
        .\run_tests.ps1            — All tests with coverage
        .\run_tests.ps1 unit       — Unit tests only
        .\run_tests.ps1 integration — Integration tests only
        .\run_tests.ps1 e2e        — End-to-end tests only
        .\run_tests.ps1 fast       — Parallel execution (pytest-xdist)
        .\run_tests.ps1 coverage   — Generate HTML coverage report
        .\run_tests.ps1 install    — Install test dependencies
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet("all", "unit", "integration", "e2e", "fast", "coverage", "install")]
    [string]$Mode = "all"
)

$ErrorActionPreference = "Stop"

switch ($Mode) {
    "install" {
        Write-Host "`n=== Installing test dependencies ===" -ForegroundColor Cyan
        python -m pip install -r requirements-test.txt
    }
    "unit" {
        Write-Host "`n=== Running Unit Tests ===" -ForegroundColor Green
        python -m pytest tests/unit -v --tb=short -m unit
    }
    "integration" {
        Write-Host "`n=== Running Integration Tests ===" -ForegroundColor Yellow
        python -m pytest tests/integration -v --tb=short -m integration
    }
    "e2e" {
        Write-Host "`n=== Running E2E Tests ===" -ForegroundColor Magenta
        python -m pytest tests/e2e -v --tb=short -m e2e
    }
    "fast" {
        Write-Host "`n=== Running All Tests (parallel) ===" -ForegroundColor Cyan
        python -m pytest -v --tb=short -n auto --cov --cov-report=term-missing
    }
    "coverage" {
        Write-Host "`n=== Generating Coverage Report ===" -ForegroundColor Blue
        python -m pytest --cov --cov-report=html --cov-report=term-missing
        Write-Host "`nHTML report: htmlcov\index.html" -ForegroundColor Green
    }
    default {
        Write-Host "`n=== Running All Tests with Coverage ===" -ForegroundColor Cyan
        python -m pytest -v --tb=short --cov --cov-report=term-missing
    }
}

$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    Write-Host "`nTests FAILED (exit code $exitCode)" -ForegroundColor Red
} else {
    Write-Host "`nAll tests PASSED" -ForegroundColor Green
}

exit $exitCode
