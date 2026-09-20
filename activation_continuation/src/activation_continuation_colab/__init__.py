"""Portable Colab execution support for the frozen activation-continuation study.

Importing this package does not mount Drive, download a model, load Torch, or
touch benchmark data. Those actions are available only through the explicit
preflight CLI after its configuration and qualification gate have been read.
"""

from .config import ColabRuntimeConfig, load_colab_runtime_config

__all__ = ["ColabRuntimeConfig", "load_colab_runtime_config"]
