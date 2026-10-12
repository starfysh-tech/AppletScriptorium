"""Model discovery and loading for LM Studio."""

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

# LM Studio installs its CLI here and does not put it on PATH by default.
_LMS_HOME = Path.home() / ".lmstudio" / "bin" / "lms"
LMS = str(_LMS_HOME) if _LMS_HOME.is_file() and os.access(_LMS_HOME, os.X_OK) else "lms"


def discover_lmstudio_models() -> List[str]:
    """
    Discover LM Studio models via `lms ls` CLI.

    Returns:
        Model names (e.g. "mistralai/mistral-7b-instruct-v0.3").
        Empty list if CLI not found.
    """
    try:
        result = subprocess.run(
            [LMS, "ls"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )
    except (FileNotFoundError, PermissionError, OSError) as exc:
        logger.warning("lms CLI not runnable (%s): %s; skipping LM Studio model discovery", LMS, exc)
        return []
    except subprocess.CalledProcessError as e:
        logger.warning(f"lms ls failed: {e.stderr}")
        return []
    except subprocess.TimeoutExpired:
        logger.warning("lms ls timed out")
        return []

    models = []
    lines = result.stdout.strip().split("\n")

    # Parse multi-column format:
    # LLM                                               PARAMS    ARCH             SIZE
    # deepseek/deepseek-r1-0528-qwen3-8b (1 variant)    8B        qwen3            4.62 GB
    # mistralai/mistral-7b-instruct-v0.3 (1 variant)    7B        Llama            4.37 GB      ✓ LOADED

    in_llm_section = False
    for line in lines:
        line_stripped = line.strip()

        # Skip empty lines
        if not line_stripped:
            continue

        # Detect LLM section header
        if line_stripped.startswith("LLM"):
            in_llm_section = True
            continue

        # Stop at EMBEDDING section
        if line_stripped.startswith("EMBEDDING"):
            break

        # Skip non-LLM lines (summary lines, etc.)
        if not in_llm_section:
            continue

        # Parse model line: extract first column (model name)
        # Model names may contain slashes, hyphens, and may have "(1 variant)" notation
        match = re.match(r"^([^\s]+(?:\s+\([^\)]+\))?)\s+", line)
        if match:
            model_name = match.group(1)
            # Remove "(N variant)" suffix
            model_name = re.sub(r"\s+\(\d+\s+variants?\)", "", model_name)
            models.append(model_name)
        else:
            logger.debug(f"Skipping lms ls line: {line_stripped}")

    logger.info(f"Discovered {len(models)} LM Studio models")
    return models


def load_lmstudio_model(model_name: str) -> None:
    """
    Load an LM Studio model via `lms load`.

    Args:
        model_name: Name of model to load

    Raises:
        subprocess.CalledProcessError: If load command fails
    """
    logger.info(f"Loading LM Studio model: {model_name}")
    result = subprocess.run(
        [LMS, "load", "--yes", model_name],
        capture_output=True,
        text=True,
        check=True,
        timeout=90
    )
    logger.info(f"Model loaded: {result.stdout.strip()}")


def unload_all_lmstudio_models() -> None:
    """
    Unload all loaded LM Studio models via `lms unload --all`.

    Raises:
        subprocess.CalledProcessError: If unload command fails
    """
    logger.info("Unloading all LM Studio models")
    result = subprocess.run(
        [LMS, "unload", "--all"],
        capture_output=True,
        text=True,
        check=True,
        timeout=60
    )
    logger.info(f"All models unloaded: {result.stdout.strip()}")
