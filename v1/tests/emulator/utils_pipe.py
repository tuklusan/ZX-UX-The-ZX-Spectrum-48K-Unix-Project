#!/usr/bin/env python3
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX Sinclair ZX Spectrum Unix
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.

"""P8.38 exact utility pipeline/error matrix metadata.

The qualification driver executes the certified P6.21 bounded-pipeline launch
fixture and checks the final utility sources for explicit read/write failure
propagation. This manifest is intentionally declarative and deterministic.
"""

STREAM_READERS = (
    "cat", "head", "wc", "rev",
)
STREAM_WRITERS = (
    "echo", "cat", "head", "wc", "env", "date", "cal", "uptime",
    "whoami", "uname", "fortune", "rev", "yes",
)
BOUNDED_PIPE_STAGES = 6
REQUIRED_ERRORS = ("E_PIPE", "E_IO", "E_NOMEM", "E_AGAIN")
FINAL_PIPELINE = ("echo", "hello", "|", "wc")

def validate_manifest() -> None:
    assert BOUNDED_PIPE_STAGES == 6
    assert FINAL_PIPELINE == ("echo", "hello", "|", "wc")
    assert "rev" in STREAM_READERS and "rev" in STREAM_WRITERS
    assert "echo" in STREAM_WRITERS
    assert len(set(STREAM_WRITERS)) == len(STREAM_WRITERS)

if __name__ == "__main__":
    validate_manifest()
