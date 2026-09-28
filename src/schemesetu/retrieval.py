from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Scheme, UserProfile


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(text.lower()))


@dataclass(frozen=True)
class RetrievedScheme:
    scheme: Scheme
    score: float


class KeywordRetriever:
    """Transparent retrieval baseline used before embeddings are added."""

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
                    scheme.benefits,
                    scheme.eligibility_text,
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
