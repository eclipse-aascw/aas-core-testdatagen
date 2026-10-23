"""Provide functionality shared accross multiple development scripts."""


def meta_model_version_in_paths(meta_model_version: str) -> str:
    """
    Construct the meta-model version as a string suitable for filesystem paths.

    >>> meta_model_version_in_paths("3.1")
    "3_1"
    """
    return meta_model_version.replace(".", "_")


DEFAULT_META_MODEL_VERSION = "3.2"
