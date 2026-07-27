from datetime import UTC, datetime

from mcplint.__about__ import __version__
from mcplint.models.common import ArtifactMetadata


def test_create_fills_version_and_timestamp() -> None:
    meta = ArtifactMetadata.create(schema_version="1.0")
    assert meta.schema_version == "1.0"
    assert meta.mcplint_version == __version__
    assert isinstance(meta.generated_at, datetime)
    assert meta.generated_at.tzinfo is UTC


def test_metadata_is_frozen_shape() -> None:
    meta = ArtifactMetadata(
        schema_version="1.0",
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
        mcplint_version="0.1.0",
    )
    assert meta.model_dump()["schema_version"] == "1.0"
