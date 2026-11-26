import re
from collections import defaultdict
from math import fsum

from app.schemas.recommendations import RecommendationBreakdown, RecommendationMatch, ReferenceMovie, SuggestedMovie
from app.services.movie_dna import MovieDNAService


REFERENCE_FEATURE_LIMIT = 16
WISH_WEIGHT = 0.6
MIN_FEATURE_COVERAGE = 0.5

ReferenceProfiles = dict[str, dict[int, tuple[str, float]]]


def build_reference_profiles(
    movie_dna: MovieDNAService, references: list[ReferenceMovie]
) -> ReferenceProfiles:
    profiles = {}
    genomes = {tmdb_id: movie_dna.get(tmdb_id) for tmdb_id in {ref.tmdb_id for ref in references}}
    for relation in ("similar", "avoid"):
        totals: dict[int, list[float]] = defaultdict(list)
        names = {}
        ids = {ref.tmdb_id for ref in references if ref.relation == relation}
        for tmdb_id in sorted(ids):
            genome = genomes[tmdb_id]
            if genome["status"] != "found":
                continue
            for tag in genome["tags"]:
                tag_id = tag["tag_id"]
                totals[tag_id].append(tag["relevance"])
                names[tag_id] = tag["name"]
        averages = {tag_id: fsum(values) / len(values) for tag_id, values in totals.items()}
        strongest = sorted(averages, key=lambda tag_id: (-averages[tag_id], tag_id))
        profile = {
            tag_id: (names[tag_id], averages[tag_id])
            for tag_id in strongest[:REFERENCE_FEATURE_LIMIT] if averages[tag_id] > 0
        }
        if profile:
            profiles[relation] = profile
    return profiles


def score_recommendation(
    suggestion: SuggestedMovie,
    profiles: ReferenceProfiles,
    candidate_scores: dict[int, float],
    feature_labels: dict[int, str],
    *,
    has_wishes: bool,
    has_references: bool,
    wish_matches: list[RecommendationMatch] | None = None,
) -> tuple[int, str, RecommendationBreakdown]:
    reference_scores = []
    evidence = []
    matches = list(wish_matches or [])
    for relation, features in profiles.items():
        known = {tag_id: weight for tag_id, (_, weight) in features.items() if tag_id in candidate_scores}
        known_weight = fsum(known.values())
        if known_weight < MIN_FEATURE_COVERAGE * fsum(weight for _, weight in features.values()):
            continue
        overlaps = {
            tag_id: min(weight, candidate_scores[tag_id]) for tag_id, weight in known.items()
        }
        similarity = 100 * fsum(overlaps.values()) / known_weight
        reference_scores.append(similarity if relation == "similar" else 100 - similarity)
        strongest = sorted(overlaps, key=lambda tag_id: (-overlaps[tag_id], tag_id))
        labels = []
        for tag_id in strongest[:3]:
            label = feature_labels.get(tag_id, "").strip()
            if overlaps[tag_id] > 0 and len(label) <= 60 and re.search(r"[А-Яа-яЁё]", label):
                labels.append(label)
        if relation == "similar":
            label = "Сходство с ориентирами"
            detail = ""
            if labels:
                detail = f"Главные совпадения — {', '.join(labels)}."
            elif similarity:
                matched_count = sum(overlap > 0 for overlap in overlaps.values())
                detail = f"Совпадения по {matched_count} из {len(known)} сопоставимых характеристик."
        else:
            label = "Различие с нежелательными ориентирами"
            detail = f"Балл снизило сходство по этим чертам — {', '.join(labels)}." if labels else ""
        score = round(reference_scores[-1])
        matches.append(RecommendationMatch(label=label, score=score, detail=detail))
        evidence.append(f"{label} — {score} из 100." + (f" {detail}" if detail else ""))

    if not reference_scores:
        summary = suggestion.reason
        basis = "Пожелания на сеанс" if has_wishes else "Оценка Gemini по запросу"
        if has_references:
            matches.append(RecommendationMatch(label="Сравнение с ориентирами", detail="Недостаточно данных для сравнения."))
        if not wish_matches:
            matches.insert(0, RecommendationMatch(label=basis, score=suggestion.relevance))
        explanation = (
            f"{basis} — {suggestion.relevance} из 100. "
            f"Сходство с ориентирами недоступно. {suggestion.reason}"
        ) if has_references else summary
        return suggestion.relevance, explanation, RecommendationBreakdown(
            chef_pick=has_references, wish_score=suggestion.relevance,
            reference_score=None, matches=matches, summary=summary,
        )

    reference_score = fsum(reference_scores) / len(reference_scores)
    explanation = " ".join(evidence)
    if len(reference_scores) > 1:
        explanation += f" Средний балл по ориентирам — {round(reference_score)} из 100."
    if has_wishes:
        score = round(WISH_WEIGHT * suggestion.relevance + (1 - WISH_WEIGHT) * reference_score)
        explanation += (
            " Итог учитывает ориентиры (40%) и пожелания (60%). "
            f"По пожеланиям — {suggestion.relevance} из 100. {suggestion.reason}"
        )
    else:
        score = round(reference_score)
    return score, explanation, RecommendationBreakdown(
        chef_pick=False, wish_score=suggestion.relevance if has_wishes else None,
        reference_score=round(reference_score), matches=matches,
        summary=suggestion.reason if has_wishes else "",
    )
