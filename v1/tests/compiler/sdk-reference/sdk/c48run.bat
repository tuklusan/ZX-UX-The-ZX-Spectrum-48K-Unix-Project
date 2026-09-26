@echo off
REM ============================================================================
REM Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
REM Proprietary rights reserved except as expressly licensed herein.
REM
REM ZX-UX C48 SDK
REM This file is governed by the SANYALnet Labs Non-Commercial License in the
REM root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
REM for AI/ML model training are prohibited unless separately authorized.
REM
REM Attribution is required: "Based on original work by Supratim Sanyal of
REM SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
REM patent, trademark, and governing-law provisions.
REM ============================================================================
python -B "%~dp0compiler\c48run.py" %*
exit /b %ERRORLEVEL%
