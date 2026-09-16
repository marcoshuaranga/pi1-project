"""Policy for turning KEDB generation attempts into explicit outcomes."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable, TypeVar


class KedbGenerationStatus(StrEnum):
    GENERATED = "generated"
    EMPTY = "empty"
    FALLBACK = "fallback"
    FAILED = "failed"


Article = TypeVar("Article")


@dataclass(frozen=True)
class KedbGenerationOutcome:
    status: KedbGenerationStatus
    articles: list[Article]
    error: Exception | None = None
    primary_error: Exception | None = None
    fallback_error: Exception | None = None


class KedbGenerationPolicy:
    """Apply primary generation, then an explicit demo fallback policy."""

    def __init__(
        self,
        primary: Callable[[], list[Article] | Article | None],
        fallback: Callable[[], Article | None],
    ):
        self.primary = primary
        self.fallback = fallback

    def run(self) -> KedbGenerationOutcome:
        try:
            result = self.primary()
        except Exception as exc:
            return self._fallback(exc)

        articles = self._as_articles(result)
        if articles:
            return KedbGenerationOutcome(KedbGenerationStatus.GENERATED, articles)
        return self._fallback()

    def _fallback(self, primary_error: Exception | None = None) -> KedbGenerationOutcome:
        try:
            article = self.fallback()
        except Exception as exc:
            return KedbGenerationOutcome(
                KedbGenerationStatus.FAILED,
                [],
                error=exc,
                primary_error=primary_error,
                fallback_error=exc,
            )
        if article is None:
            if primary_error:
                return KedbGenerationOutcome(
                    KedbGenerationStatus.FAILED,
                    [],
                    error=primary_error,
                    primary_error=primary_error,
                )
            return KedbGenerationOutcome(
                KedbGenerationStatus.EMPTY,
                [],
            )
        return KedbGenerationOutcome(
            KedbGenerationStatus.FALLBACK,
            [article],
            error=primary_error,
            primary_error=primary_error,
        )

    @staticmethod
    def _as_articles(result: list[Article] | Article | None) -> list[Article]:
        if result is None:
            return []
        if isinstance(result, list):
            return result
        return [result]