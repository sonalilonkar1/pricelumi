"""W1-25: deterministic, conservative product-offer matching baseline.

Not a trained model and not a production-ready retailer data adapter.
The matcher consumes normalized/temporary ProductOffer-like dictionaries.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class MatchResult:
    decision: str  # "match", "non_match", or "uncertain"
    reason: str
    evidence: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def compact(value: Any) -> str:
    """Normalize capitalization, spaces and punctuation for identity fields."""
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def normalize_gtin(value: Any) -> str | None:
    """Validate GTIN-8/12/13/14 checksums; compare in zero-padded GTIN-14 form."""
    if value is None:
        return None
    raw = str(value).strip()
    if not re.fullmatch(r"[0-9\s-]+", raw):
        return None
    digits = re.sub(r"[\s-]", "", raw)
    if len(digits) not in (8, 12, 13, 14):
        return None
    body, check = digits[:-1], int(digits[-1])
    score = sum(int(n) * (3 if i % 2 == 0 else 1)
                for i, n in enumerate(reversed(body)))
    if (10 - score % 10) % 10 != check:
        return None
    return digits.zfill(14)


def variant_map(record: Mapping[str, Any]) -> dict[str, str]:
    raw = record.get("variants") or {}
    if not isinstance(raw, Mapping):
        return {}
    result: dict[str, str] = {}
    for key, value in raw.items():
        k, v = compact(key), compact(value)
        if k and v:
            result[k] = v
    return result


def is_accessory(record: Mapping[str, Any]) -> bool:
    """Detect explicitly described accessories in product titles."""
    title = str(record.get("title") or "").casefold()

    accessory_phrases = (
        "carrying case",
        "protective case",
        "replacement ear pads",
        "replacement earpads",
    )

    return any(phrase in title for phrase in accessory_phrases)


def extract_title_ram(title: str) -> int | None:
    """Extract RAM capacity from a product title, if explicitly stated."""
    title = str(title or "").casefold()

    patterns = [
        r"\b(\d+)\s*gb\s*(?:ram|memory)\b",
        r"\b(?:ram|memory)\s*[:\-]?\s*(\d+)\s*gb\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            return int(match.group(1))

    return None


def has_ram_conflict(record: Mapping[str, Any]) -> bool:
    """Check whether title RAM contradicts the structured RAM field."""
    title_ram = extract_title_ram(record.get("title", ""))

    variants = variant_map(record)
    structured_ram = variants.get("ram") or variants.get("memory")

    if title_ram is None or not structured_ram:
        return False

    match = re.fullmatch(r"(\d+)gb", structured_ram)

    if not match:
        return False

    return title_ram != int(match.group(1))


def extract_title_storage(title: str) -> str | None:
    """Extract storage capacity without confusing it with RAM."""
    title = str(title or "").casefold()
    capacities = []

    for match in re.finditer(
        r"\b(\d+(?:\.\d+)?)\s*(gb|tb)\b", title
    ):
        before = title[max(0, match.start() - 12):match.start()]
        after = title[match.end():match.end() + 12]

        # Ignore capacities explicitly referring to RAM.
        if re.search(r"\b(?:ram|memory|vram)\s*:?\s*$", before):
            continue

        if re.match(r"\s*(?:ram|memory|vram)\b", after):
            continue

        capacities.append(compact(match.group(0)))

    # Avoid guessing if multiple possible storage capacities appear.
    if len(capacities) != 1:
        return None

    return capacities[0]


def has_storage_conflict(record: Mapping[str, Any]) -> bool:
    """Check if title storage contradicts structured storage."""
    title_storage = extract_title_storage(record.get("title", ""))
    structured_storage = variant_map(record).get("storage")

    if not title_storage or not structured_storage:
        return False

    return title_storage != structured_storage



def match_products(a: Mapping[str, Any], b: Mapping[str, Any]) -> MatchResult:
    """Compare two offers; avoid confident matches when key evidence is missing.

    `price_usd`, `retailer` and `title` are deliberately not identity keys.
    Variant disagreements are hard negatives even when titles are similar.
    """
    ba, bb = compact(a.get("brand")), compact(b.get("brand"))
    ma, mb = compact(a.get("model")), compact(b.get("model"))
    va, vb = variant_map(a), variant_map(b)

    if has_storage_conflict(a) or has_storage_conflict(b):
        return MatchResult(
            "uncertain",
            "Product title contradicts structured storage specification",
            "storage_data_conflict"
        )

    if has_ram_conflict(a) or has_ram_conflict(b):
        return MatchResult(
            "uncertain",
            "Product title contradicts structured RAM specification",
            "ram_data_conflict"
        )

    if is_accessory(a) != is_accessory(b):
        return MatchResult(
            "non_match",
            "Main product and accessory must not be merged",
            "product_type_conflict"
        )

    # All remaining matching rules stay unchanged.


    if has_ram_conflict(a) or has_ram_conflict(b):
        return MatchResult(
            "uncertain",
            "Product title contradicts structured RAM specification",
            "ram_data_conflict"
        )



    if is_accessory(a) != is_accessory(b):
        return MatchResult(
            "non_match",
            "Main product and accessory must not be merged",
            "product_type_conflict"
        )


    if ba and bb and ba != bb:
        return MatchResult("non_match", "Brand differs", "brand")
    if ma and mb and ma != mb:
        return MatchResult("non_match", "Model differs", "model")

    for field in sorted(va.keys() & vb.keys()):
        if va[field] != vb[field]:
            return MatchResult("non_match", f"Variant '{field}' differs", "variant_conflict")

    ga, gb = normalize_gtin(a.get("gtin")), normalize_gtin(b.get("gtin"))
    pa, pb = compact(a.get("mpn")), compact(b.get("mpn"))

    # Conflicting authoritative-looking identifiers are not overridden by a
    # similar title or model. MPN is only meaningful with an agreed brand.
    if ga and gb and ga != gb:
        return MatchResult("uncertain", "Both valid GTINs differ; needs review", "gtin_conflict")
    if ba and bb and pa and pb and pa != pb:
        return MatchResult("uncertain", "Manufacturer part numbers differ", "mpn_conflict")
    if ga and gb and ga == gb:
        return MatchResult("match", "Validated GTIN matches with no observed conflicts", "gtin")
    if ba and bb and ba == bb and pa and pb and pa == pb:
        return MatchResult("match", "Brand and MPN match with no observed conflicts", "brand_mpn")

    # When exact IDs aren't available, require full variant coverage on both
    # sides (no missing-on-one-side attributes), and at least one informative
    # variant besides condition. More permissive matching can be added later
    # after evaluating real retailer data.
    if not (ba and bb and ba == bb and ma and mb and ma == mb):
        return MatchResult("uncertain", "Insufficient brand/model identity fields", "missing_identity")
    if va.keys() != vb.keys():
        return MatchResult("uncertain", "Variant attributes are incomplete", "missing_variant")
    if not (va.keys() - {"condition"}):
        return MatchResult("uncertain", "No identifying variant attributes", "weak_attributes")
    return MatchResult("match", "Normalized brand, model and variants match", "attributes")
