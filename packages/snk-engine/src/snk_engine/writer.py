"""Écriture en fragments (shards) Parquet ou JSONL, compatibles Hugging Face."""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .generator import Sample

SCHEMA = pa.schema(
    [
        ("id", pa.int64()),
        ("snk", pa.string()),
        ("fr", pa.string()),
        ("template_id", pa.string()),
        ("source", pa.string()),
    ]
)


class ShardWriter:
    def __init__(self, out_dir: Path, split: str = "train", shard_size: int = 1_000_000, fmt: str = "parquet") -> None:
        if fmt not in {"parquet", "jsonl"}:
            raise ValueError("fmt doit être 'parquet' ou 'jsonl'")
        self.dir = out_dir / "data"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.split, self.shard_size, self.fmt = split, shard_size, fmt
        self.buffer: list[dict] = []
        self.shard = 0
        self.count = 0
        self.files: list[Path] = []

    def write(self, sample: Sample) -> None:
        self.buffer.append(
            {"id": self.count, "snk": sample.snk, "fr": sample.fr, "template_id": sample.template_id, "source": "synthetic"}
        )
        self.count += 1
        if len(self.buffer) >= self.shard_size:
            self.flush()

    def flush(self) -> None:
        if not self.buffer:
            return
        path = self.dir / f"{self.split}-{self.shard:05d}.{self.fmt}"
        if self.fmt == "parquet":
            pq.write_table(pa.Table.from_pylist(self.buffer, schema=SCHEMA), path, compression="zstd")
        else:
            with path.open("w", encoding="utf-8") as f:
                for row in self.buffer:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.files.append(path)
        self.buffer.clear()
        self.shard += 1

    def __enter__(self) -> "ShardWriter":
        return self

    def __exit__(self, *exc) -> None:
        self.flush()
