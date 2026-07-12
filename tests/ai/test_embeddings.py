import math

import pytest

from api.ai.embeddings import (
    EmbeddingIdentity,
    EmbeddingValidationError,
    EmbeddingValue,
    ProductionEmbeddingUnavailableError,
    embed_with_production_provider,
)


def _identity() -> EmbeddingIdentity:
    return EmbeddingIdentity(
        model_id="text-embedding-3-small",
        dimensions=3,
        normalized=True,
        input_type="catalog_item",
        input_version="v1",
    )


def test_embedding_value_preserves_complete_identity_and_freezes_vector() -> None:
    source = [0, 0.5, -1]

    value = EmbeddingValue(identity=_identity(), vector=source)
    source[0] = 1

    assert value.identity == _identity()
    assert value.vector == (0.0, 0.5, -1.0)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("model_id", " "),
        ("dimensions", 0),
        ("dimensions", True),
        ("normalized", "true"),
        ("input_type", ""),
        ("input_version", " "),
    ],
)
def test_embedding_identity_rejects_invalid_metadata(field: str, invalid_value: object) -> None:
    fields: dict[str, object] = {
        "model_id": "text-embedding-3-small",
        "dimensions": 3,
        "normalized": True,
        "input_type": "catalog_item",
        "input_version": "v1",
    }
    fields[field] = invalid_value

    with pytest.raises(EmbeddingValidationError):
        EmbeddingIdentity(**fields)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "vector",
    [
        [1, 2],
        [1, 2, 3, 4],
        [0, math.nan, 1],
        [0, math.inf, 1],
        [0, True, 1],
        "not-a-vector",
    ],
)
def test_embedding_value_rejects_wrong_dimension_or_nonfinite_components(vector: object) -> None:
    with pytest.raises(EmbeddingValidationError):
        EmbeddingValue(identity=_identity(), vector=vector)  # type: ignore[arg-type]


def test_production_embedding_raises_explicit_unavailable_error_without_fallback() -> None:
    identity = _identity()

    with pytest.raises(ProductionEmbeddingUnavailableError) as raised:
        embed_with_production_provider(identity=identity, text="cabinet hinge")

    assert raised.value.identity is identity
    assert "text-embedding-3-small" in str(raised.value)
    assert "cabinet hinge" not in str(raised.value)
