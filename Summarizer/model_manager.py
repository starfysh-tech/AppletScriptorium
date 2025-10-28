"""Model discovery and management for LM Studio and Ollama backends."""

import logging
import re
import subprocess
from dataclasses import dataclass
from typing import Literal, List

Backend = Literal["lmstudio", "ollama"]

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Represents a model available on a backend."""
    backend: Backend
    name: str  # e.g., "qwen3:latest", "mistral-7b"
    loaded: bool  # For LM Studio: True if loaded, False if available


def discover_lmstudio_models() -> List[ModelInfo]:
    """
    Discover LM Studio models via `lms ls` CLI.

    Returns:
        List of ModelInfo objects with backend="lmstudio".
        Empty list if CLI not found.
    """
    try:
        result = subprocess.run(
            ["lms", "ls"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )
    except FileNotFoundError:
        logger.warning("lms CLI not found; skipping LM Studio model discovery")
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

        # Parse model line: extract first column (model name) and check for "✓ LOADED" suffix
        # Model names may contain slashes, hyphens, and may have "(1 variant)" notation
        match = re.match(r"^([^\s]+(?:\s+\([^\)]+\))?)\s+", line)
        if match:
            model_name = match.group(1)
            # Remove "(N variant)" suffix
            model_name = re.sub(r"\s+\(\d+\s+variants?\)", "", model_name)
            # Check if line ends with "✓ LOADED"
            loaded = "✓ LOADED" in line
            models.append(ModelInfo(backend="lmstudio", name=model_name, loaded=loaded))
        else:
            logger.debug(f"Skipping lms ls line: {line_stripped}")

    logger.info(f"Discovered {len(models)} LM Studio models")
    return models


def discover_ollama_models() -> List[ModelInfo]:
    """
    Discover Ollama models via `ollama list` CLI.

    Returns:
        List of ModelInfo objects with backend="ollama", loaded=True.
        Empty list if CLI not found.
    """
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )
    except FileNotFoundError:
        logger.warning("ollama CLI not found; skipping Ollama model discovery")
        return []
    except subprocess.CalledProcessError as e:
        logger.warning(f"ollama list failed: {e.stderr}")
        return []
    except subprocess.TimeoutExpired:
        logger.warning("ollama list timed out")
        return []

    models = []
    lines = result.stdout.strip().split("\n")

    # Skip header row (NAME ID SIZE)
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue

        # Parse: "qwen3:latest         abc123        4.7GB"
        # Extract first column (model name)
        parts = line.split()
        if parts:
            model_name = parts[0]
            # All Ollama models are considered loaded (pulled = loaded)
            models.append(ModelInfo(backend="ollama", name=model_name, loaded=True))
        else:
            logger.warning(f"Failed to parse ollama list line: {line}")

    logger.info(f"Discovered {len(models)} Ollama models")
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
        ["lms", "load", model_name],
        capture_output=True,
        text=True,
        check=True,
        timeout=60
    )
    logger.info(f"Model loaded: {result.stdout.strip()}")


def unload_lmstudio_model(model_name: str) -> None:
    """
    Unload an LM Studio model via `lms unload`.

    Args:
        model_name: Name of model to unload

    Raises:
        subprocess.CalledProcessError: If unload command fails
    """
    logger.info(f"Unloading LM Studio model: {model_name}")
    result = subprocess.run(
        ["lms", "unload", model_name],
        capture_output=True,
        text=True,
        check=True,
        timeout=30
    )
    logger.info(f"Model unloaded: {result.stdout.strip()}")


def get_available_models(backends: List[Backend] = None) -> List[ModelInfo]:
    """
    Discover models across specified backends.

    Args:
        backends: List of backends to query. Defaults to ["lmstudio", "ollama"].

    Returns:
        Combined list of ModelInfo objects from all backends.
    """
    if backends is None:
        backends = ["lmstudio", "ollama"]

    models = []

    if "lmstudio" in backends:
        models.extend(discover_lmstudio_models())

    if "ollama" in backends:
        models.extend(discover_ollama_models())

    logger.info(f"Total models discovered: {len(models)}")
    return models
