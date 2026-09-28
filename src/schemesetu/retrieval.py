"""Scheme and passage retrieval: keyword baseline plus configurable embeddings."""

from __future__ import annotations

import hashlib
import math
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Protocol

from .models import RetrievedEvidence, Scheme, SourcePassage, UserProfile
from .passages import build_passages

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(text.lower()))


def _token_list(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


@dataclass(frozen=True)
class RetrievedScheme:
    scheme: Scheme
    score: float
    evidence: tuple[RetrievedEvidence, ...] = ()


class KeywordRetriever:
    """Transparent scheme-level keyword retrieval baseline."""

    def search(
        self,
        query: str,
        profile: UserProfile,
        schemes: list[Scheme],
        top_k: int = 5,
    ) -> list[RetrievedScheme]:
        profile_terms = [
            profile.state,
            profile.gender,
            profile.category,
            profile.education_level,
            profile.course,
        ]
        query_tokens = _tokens(" ".join([query, *[v for v in profile_terms if v]]))
        scored: list[RetrievedScheme] = []

        for scheme in schemes:
            searchable = " ".join(
                [
                    scheme.name,
                    scheme.description,
                    scheme.detailed_description,
                    scheme.benefits,
                    scheme.eligibility_text,
                    scheme.exclusions_text,
                    scheme.documents_text,
                    scheme.references_text,
                    " ".join(scheme.categories),
                    " ".join(scheme.states),
                ]
            )
            scheme_tokens = _tokens(searchable)
            overlap = len(query_tokens & scheme_tokens)
            score = overlap / max(len(query_tokens), 1)

            if profile.state and scheme.states:
                normalized_states = {state.casefold() for state in scheme.states}
                if profile.state.casefold() in normalized_states or "all india" in normalized_states:
                    score += 0.25
                else:
                    score -= 0.20

            if score > 0:
                scored.append(RetrievedScheme(scheme=scheme, score=round(score, 4)))

        return sorted(scored, key=lambda item: (-item.score, item.scheme.name))[:top_k]


class KeywordPassageRetriever:
    """Passage-level keyword retrieval with scheme/section/source attribution."""

    method = "keyword"

    def search(
        self,
        query: str,
        passages: list[SourcePassage],
        top_k: int = 8,
    ) -> list[RetrievedEvidence]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []
        scored: list[RetrievedEvidence] = []
        for passage in passages:
            passage_tokens = _tokens(passage.text)
            if not passage_tokens:
                continue
            overlap = len(query_tokens & passage_tokens)
            if overlap == 0:
                continue
            score = overlap / max(len(query_tokens), 1)
            scored.append(
                RetrievedEvidence(
                    scheme_id=passage.scheme_id,
                    scheme_name=passage.scheme_name,
                    section=passage.section,
                    text=passage.text,
                    source_url=passage.source_url,
                    score=round(score, 4),
                    retrieval_method=self.method,
                )
            )
        return sorted(scored, key=lambda item: (-item.score, item.scheme_id, item.section))[:top_k]


class EmbeddingProvider(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class LocalHashEmbeddingProvider:
    """Deterministic offline embedding for local comparison without API keys.

    Uses hashed bag-of-words features. Not a substitute for a measured
    evaluation with a reviewed set; it only enables provider wiring and tests.
    """

    name = "local"

    def __init__(self, dimensions: int = 256):
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = _token_list(text)
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class OpenAIEmbeddingProvider:
    """OpenAI embeddings when OPENAI_API_KEY is present."""

    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-3-small",
        base_url: str = "https://api.openai.com/v1",
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model
        self.base_url = base_url.rstrip("/")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for the openai embedding provider")

    def embed(self, texts: list[str]) -> list[list[float]]:
        import json
        from urllib import request

        payload = json.dumps({"model": self.model, "input": texts}).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/embeddings",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
        ordered = sorted(body["data"], key=lambda item: item["index"])
        return [item["embedding"] for item in ordered]


def get_embedding_provider(name: str | None = None) -> EmbeddingProvider:
    provider = (name or os.environ.get("SCHEMESETU_EMBEDDING_PROVIDER", "local")).casefold()
    if provider in {"local", "hash"}:
        return LocalHashEmbeddingProvider()
    if provider == "openai":
        return OpenAIEmbeddingProvider()
    raise ValueError(f"Unknown embedding provider: {provider}")


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


class EmbeddingPassageRetriever:
    """Passage retrieval via a configurable embedding provider."""

    method = "embedding"

    def __init__(self, provider: EmbeddingProvider | None = None):
        self.provider = provider or get_embedding_provider()
        self._cache: dict[str, list[float]] | None = None
        self._passage_ids: list[str] = []
        self._passages: list[SourcePassage] = []

    def index(self, passages: list[SourcePassage]) -> None:
        self._passages = passages
        self._passage_ids = [f"{p.scheme_id}:{p.section}:{i}" for i, p in enumerate(passages)]
        vectors = self.provider.embed([p.text for p in passages]) if passages else []
        self._cache = {pid: vector for pid, vector in zip(self._passage_ids, vectors)}

    def search(
        self,
        query: str,
        passages: list[SourcePassage] | None = None,
        top_k: int = 8,
    ) -> list[RetrievedEvidence]:
        if passages is not None and (
            self._cache is None
            or len(passages) != len(self._passages)
            or any(a.scheme_id != b.scheme_id or a.section != b.section for a, b in zip(passages, self._passages))
        ):
            self.index(passages)
        if self._cache is None:
            self.index(passages or [])
        if not self._passages:
            return []
        query_vector = self.provider.embed([query])[0]
        scored: list[RetrievedEvidence] = []
        for passage_id, passage in zip(self._passage_ids, self._passages):
            score = _cosine(query_vector, self._cache[passage_id])
            if score <= 0:
                continue
            scored.append(
                RetrievedEvidence(
                    scheme_id=passage.scheme_id,
                    scheme_name=passage.scheme_name,
                    section=passage.section,
                    text=passage.text,
                    source_url=passage.source_url,
                    score=round(float(score), 4),
                    retrieval_method=f"{self.method}:{self.provider.name}",
                )
            )
        return sorted(scored, key=lambda item: (-item.score, item.scheme_id, item.section))[:top_k]


class HybridSchemeRetriever:
    """Retrieve schemes by aggregating passage evidence from a chosen method."""

    def __init__(
        self,
        method: str | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        passages_per_scheme: int = 3,
    ):
        self.method = (method or os.environ.get("SCHEMESETU_RETRIEVAL", "keyword")).casefold()
        self.keyword_schemes = KeywordRetriever()
        self.keyword_passages = KeywordPassageRetriever()
        self.embedding_passages = EmbeddingPassageRetriever(embedding_provider)
        self.passages_per_scheme = passages_per_scheme
        self._passages: list[SourcePassage] = []

    def prepare(self, schemes: list[Scheme]) -> None:
        self._passages = build_passages(schemes)
        if self.method.startswith("embedding"):
            self.embedding_passages.index(self._passages)

    def search(
        self,
        query: str,
        profile: UserProfile,
        schemes: list[Scheme],
        top_k: int = 5,
    ) -> list[RetrievedScheme]:
        if not self._passages:
            self.prepare(schemes)

        profile_terms = [
            profile.state,
            profile.gender,
            profile.category,
            profile.education_level,
            profile.course,
        ]
        enriched_query = " ".join([query, *[v for v in profile_terms if v]])

        if self.method in {"keyword", "keyword_passages"}:
            evidence = self.keyword_passages.search(enriched_query, self._passages, top_k=top_k * 4)
            if self.method == "keyword" and not evidence:
                # Fall back to legacy scheme scoring when passages do not match.
                return self.keyword_schemes.search(query, profile, schemes, top_k=top_k)
        elif self.method.startswith("embedding"):
            evidence = self.embedding_passages.search(enriched_query, self._passages, top_k=top_k * 4)
        else:
            raise ValueError(f"Unknown retrieval method: {self.method}")

        by_scheme: dict[str, list[RetrievedEvidence]] = defaultdict(list)
        for item in evidence:
            by_scheme[item.scheme_id].append(item)

        scheme_index = {scheme.scheme_id: scheme for scheme in schemes}
        scored: list[RetrievedScheme] = []
        for scheme_id, items in by_scheme.items():
            scheme = scheme_index.get(scheme_id)
            if scheme is None:
                continue
            score = max(item.score for item in items)
            if profile.state and scheme.states:
                normalized_states = {state.casefold() for state in scheme.states}
                if profile.state.casefold() in normalized_states or "all india" in normalized_states:
                    score += 0.25
                else:
                    score -= 0.20
            top_evidence = tuple(
                sorted(items, key=lambda item: (-item.score, item.section))[: self.passages_per_scheme]
            )
            if score > 0:
                scored.append(
                    RetrievedScheme(
                        scheme=scheme,
                        score=round(score, 4),
                        evidence=top_evidence,
                    )
                )
        return sorted(scored, key=lambda item: (-item.score, item.scheme.name))[:top_k]


def compare_retrieval_methods(
    query: str,
    schemes: list[Scheme],
    top_k: int = 5,
    embedding_provider: EmbeddingProvider | None = None,
) -> dict[str, object]:
    """Return side-by-side top scheme IDs for keyword vs embedding passage retrieval.

    Does not invent evaluation metrics; only reports overlapping IDs from the
    current catalog for manual review.
    """
    passages = build_passages(schemes)
    keyword = KeywordPassageRetriever().search(query, passages, top_k=top_k * 3)
    embedding = EmbeddingPassageRetriever(embedding_provider or get_embedding_provider()).search(
        query, passages, top_k=top_k * 3
    )
    keyword_ids = list(dict.fromkeys(item.scheme_id for item in keyword))[:top_k]
    embedding_ids = list(dict.fromkeys(item.scheme_id for item in embedding))[:top_k]
    overlap = [scheme_id for scheme_id in keyword_ids if scheme_id in set(embedding_ids)]
    return {
        "query": query,
        "keyword_scheme_ids": keyword_ids,
        "embedding_scheme_ids": embedding_ids,
        "overlap_scheme_ids": overlap,
        "embedding_provider": (embedding_provider or get_embedding_provider()).name,
        "note": (
            "Overlap counts are not evaluation scores. Measured retrieval quality "
            "requires an independently reviewed evaluation set."
        ),
    }
