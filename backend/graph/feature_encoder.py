import numpy as np
import hashlib
from typing import Dict, List


class FeatureEncoder:
    def __init__(self, embedding_dim: int = 64):
        self.embedding_dim = embedding_dim
        self.type_vocab = {}
        self.token_dim = embedding_dim // 3
        self.type_dim = embedding_dim // 3
        self.pos_dim = embedding_dim - 2 * (embedding_dim // 3)
        self._rng = np.random.RandomState(42)
        self._type_embeddings = {}
        self._token_cache = {}

    def encode(self, program_graph: Dict) -> Dict:
        raw_features = program_graph['node_features_raw']
        node_ids = program_graph['node_ids']
        n = len(raw_features)

        if n == 0:
            return {
                'node_embeddings': np.zeros((0, self.embedding_dim)),
                'node_ids': [],
            }

        embeddings = np.zeros((n, self.embedding_dim), dtype=np.float32)

        for i, feat in enumerate(raw_features):
            type_emb = self._get_type_embedding(feat['type'])
            token_emb = self._get_token_embedding(feat['token'])
            pos_emb = self._get_positional_encoding(
                feat['depth'],
                feat['in_degree'],
                feat['out_degree'],
                feat['num_children']
            )
            embeddings[i] = np.concatenate([type_emb, token_emb, pos_emb])

        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-8)
        embeddings = embeddings / norms

        return {
            'node_embeddings': embeddings,
            'node_ids': node_ids,
        }

    def _get_type_embedding(self, node_type: str) -> np.ndarray:
        if node_type not in self._type_embeddings:
            seed = int(hashlib.md5(node_type.encode()).hexdigest()[:8], 16)
            rng = np.random.RandomState(seed)
            emb = rng.randn(self.type_dim).astype(np.float32) * 0.1
            self._type_embeddings[node_type] = emb
        return self._type_embeddings[node_type]

    def _get_token_embedding(self, token: str) -> np.ndarray:
        if not token:
            return np.zeros(self.token_dim, dtype=np.float32)
        if token not in self._token_cache:
            seed = int(hashlib.md5(token.encode()).hexdigest()[:8], 16)
            rng = np.random.RandomState(seed)
            emb = rng.randn(self.token_dim).astype(np.float32) * 0.1
            self._token_cache[token] = emb
        return self._token_cache[token]

    def _get_positional_encoding(self, depth: int, in_deg: int, out_deg: int, children: int) -> np.ndarray:
        pe = np.zeros(self.pos_dim, dtype=np.float32)
        if self.pos_dim >= 4:
            pe[0] = np.tanh(depth / 10.0)
            pe[1] = np.tanh(in_deg / 5.0)
            pe[2] = np.tanh(out_deg / 5.0)
            pe[3] = np.tanh(children / 10.0)

        for k in range(4, self.pos_dim):
            freq = 1.0 / (10000 ** (2 * (k // 2) / self.pos_dim))
            if k % 2 == 0:
                pe[k] = np.sin(depth * freq)
            else:
                pe[k] = np.cos(depth * freq)

        return pe
