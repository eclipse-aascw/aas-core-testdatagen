# SPDX-FileCopyrightText: 2025 aas-core-testdatagen AUTHORS
#
# SPDX-License-Identifier: MIT

"""Download the latest meta-model for V3.0 to the test data."""

import argparse
import os
import pathlib
import sys
from typing import Final, Mapping, Union

import black
import requests

_OWNER: Final[str] = "aas-core-works"
_REPO: Final[str] = "aas-core-meta"
_REF: Final[str] = "main"

# NOTE (aaronzi, 2026-11-05):
# The meta-model is copied verbatim from aas-core-meta, so we attribute it to
# its authors. Older upstream revisions do not carry a license header, so we
# prepend it unless the downloaded content already includes one.
#
# REUSE-IgnoreStart
_META_MODEL_LICENSE_HEADER = """\
# SPDX-FileCopyrightText: 2024 aas-core-meta AUTHORS
#
# SPDX-License-Identifier: MIT

"""
# REUSE-IgnoreEnd


def _latest_commit_sha(remote_path: str, timeout: float = 15.0) -> str:
    """Resolve the latest commit SHA on the ``REF`` for a specific path."""
    params: Mapping[str, Union[str, int]] = {
        "path": remote_path,
        "sha": _REF,
        "per_page": 1,
    }
    resp = requests.get(
        f"https://api.github.com/repos/{_OWNER}/{_REPO}/commits",
        params=params,
        timeout=timeout,
    )
    try:
        resp.raise_for_status()
    except requests.HTTPError as ex:
        raise RuntimeError(
            f"Failed to resolve latest commit for "
            f"{_OWNER}/{_REPO}:{_REF} path={remote_path} "
            f"({resp.status_code}): {resp.text}"
        ) from ex

    commits = resp.json()
    if not commits or not isinstance(commits, list):
        raise RuntimeError(
            "Could not determine latest commit SHA (empty API response)."
        )

    sha = commits[0].get("sha")
    if not isinstance(sha, str):
        raise RuntimeError("API did not return a valid commit SHA.")

    if len(sha) == 0:
        raise RuntimeError("API returned an empty commit SHA.")

    return sha


def _raw_url(sha: str, remote_path: str) -> str:
    """Get the URL of the raw file on GitHub."""
    return f"https://raw.githubusercontent.com/{_OWNER}/{_REPO}/{sha}/{remote_path}"


def _download(url: str, timeout: float = 30.0) -> str:
    """Download the raw file contents."""
    resp = requests.get(url, timeout=timeout)
    try:
        resp.raise_for_status()
    except requests.HTTPError as ex:
        raise RuntimeError(
            f"Failed to download file from {url} ({resp.status_code}): {resp.text}"
        ) from ex

    return resp.text


def main() -> int:
    """Execute the main routine."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--meta_model_version",
        help="Version of the meta-model which we want to update (*e.g.*, '3.1')",
        required=True,
    )
    args = parser.parse_args()

    meta_model_version = str(args.meta_model_version)

    meta_model_version_in_paths = meta_model_version.replace(".", "_")

    meta_model_filename = f"v{meta_model_version_in_paths}.py"

    remote_path = f"aas_core_meta/{meta_model_filename}"

    sha = _latest_commit_sha(remote_path=remote_path)

    raw_url = _raw_url(sha=sha, remote_path=remote_path)

    content = _download(url=raw_url)

    banner = f"# Downloaded from: {raw_url}\n# Do NOT edit or append!"

    repo_root = pathlib.Path(os.path.realpath(__file__)).parent.parent.parent

    out_path = repo_root / "dev/test_data/meta_model" / meta_model_filename
    out_path.parent.mkdir(exist_ok=True)

    # REUSE-IgnoreStart
    license_header = (
        "" if "SPDX-License-Identifier:" in content else _META_MODEL_LICENSE_HEADER
    )
    # REUSE-IgnoreEnd

    out_path.write_text(
        f"{license_header}{banner}\n\n{content.rstrip()}\n\n{banner}",
        encoding="utf-8",
    )

    black.format_file_in_place(
        src=out_path, fast=False, mode=black.FileMode(), write_back=black.WriteBack.YES
    )

    print(f"Downloaded and reformatted to: {out_path} (from commit {sha[:8]}).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
