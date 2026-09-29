@echo off
REM ============================================================================
REM Copyright (c) 2026 SANYALnet Labs.
REM Proprietary rights reserved except as expressly licensed herein.
REM
REM ZX-UX C48 SDK
REM This file is governed by the SANYALnet Labs Non-Commercial License in the
REM root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
REM restricted model training is prohibited unless separately authorized.
REM
REM Attribution required: SANYALnet Labs. See LICENSE for full terms,
REM warranty disclaimer, termination, patent, trademark, and governing-law
REM provisions.
REM ============================================================================
python -B "%~dp0compiler\c48srctap.py" %*
exit /b %ERRORLEVEL%
