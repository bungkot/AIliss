from difflib import SequenceMatcher

from ailiss.extraction import canonicalize_domain, normalize_company_name


def domain_match(left: str | None, right: str | None) -> float:
    left_domain = canonicalize_domain(left) if left else None
    right_domain = canonicalize_domain(right) if right else None
    if left_domain and right_domain and left_domain == right_domain:
        return 1.0
    return 0.0


def exact_name_match(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    left_name = normalize_company_name(left)
    right_name = normalize_company_name(right)
    return 1.0 if left_name == right_name else 0.0


def similarity_score(left: str, right: str) -> float:
    return SequenceMatcher(
        None, normalize_company_name(left), normalize_company_name(right)
    ).ratio()


def resolve_company_match(
    left_name: str,
    left_domain: str | None,
    right_name: str,
    right_domain: str | None,
) -> tuple[float, str]:
    domain_score = domain_match(left_domain, right_domain)
    if domain_score == 1.0:
        return 1.0, "canonical_domain"
    exact_score = exact_name_match(left_name, right_name)
    if exact_score == 1.0:
        return 1.0, "exact_normalized_name"
    similarity = similarity_score(left_name, right_name)
    if similarity >= 0.85:
        return similarity, "similarity_candidate"
    return similarity, "no_match"
