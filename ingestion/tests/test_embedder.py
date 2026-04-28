import pytest
from unittest.mock import MagicMock, patch

import embedder as _embedder_module
from embedder import embed_batch


@pytest.fixture(autouse=True)
def reset_client():
    _embedder_module._client = None
    yield
    _embedder_module._client = None


class TestEmbedBatch:
    def test_returns_list_of_vectors(self):
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024, [0.2] * 1024]

        with patch("embedder.voyageai.Client") as mock_client_cls:
            mock_client_cls.return_value.embed.return_value = mock_result
            vectors = embed_batch(["text one", "text two"])

        assert len(vectors) == 2
        assert len(vectors[0]) == 1024

    def test_passes_correct_model(self):
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024]

        with patch("embedder.voyageai.Client") as mock_client_cls:
            mock_instance = mock_client_cls.return_value
            mock_instance.embed.return_value = mock_result
            embed_batch(["text"], model="voyage-3")

        mock_instance.embed.assert_called_once_with(["text"], model="voyage-3")

    def test_empty_input_returns_empty_list(self):
        mock_result = MagicMock()
        mock_result.embeddings = []

        with patch("embedder.voyageai.Client") as mock_client_cls:
            mock_client_cls.return_value.embed.return_value = mock_result
            vectors = embed_batch([])

        assert vectors == []
