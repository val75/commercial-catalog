"""The folder of original uploads, one file per document, named by its SHA-256.

The database stores the name relative to the folder, so the folder can move.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


class OriginalStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def save(self, data: bytes, sha256: str, suffix: str) -> str:
        """Write the original and return the path to store on its document."""
        name = f"{sha256}{suffix}"
        self.root.mkdir(parents=True, exist_ok=True)
        # Write then rename, so a crash never leaves half a file under the final name.
        handle, temporary = tempfile.mkstemp(dir=self.root, prefix=".upload-")
        try:
            with os.fdopen(handle, "wb") as file:
                file.write(data)
            os.replace(temporary, self.root / name)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
        return name

    def read(self, path: str) -> bytes:
        return self._resolve(path).read_bytes()

    def delete(self, path: str) -> None:
        self._resolve(path).unlink(missing_ok=True)

    def _resolve(self, path: str) -> Path:
        resolved = (self.root / path).resolve()
        if resolved.parent != self.root.resolve():
            raise ValueError(f"{path!r} isn't a file in the originals folder.")
        return resolved
