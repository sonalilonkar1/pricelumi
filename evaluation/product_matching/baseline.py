
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
    score = sum(
        int(n) * (3 if i % 2 == 0 else 1)
        for i, n in enumerate(reversed(body))
    )

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


def offer_kind(record: Mapping[str, Any]) -> str:
    """Conservatively classify an offer as product, accessory, or bundle.

    Heuristics intentionally recognize *explicit* language only. Ambiguous
    accessory types and bundle contents still require structured retailer data.
    """
    title = str(record.get("title") or "").casefold()

    # Check bundles first: "phone with protective case" is not a standalone case.
    bundle_patterns = (
        r"\b(?:bundle|bundled|combo|value pack|starter kit)\b",
        r"\b(?:[2-9][ -]?pack|pack of [2-9]|multi[ -]?pack)\b",
        r"\b(?:with|includes?|plus)\s+(?:an?\s+|the\s+)?"
        r"(?:extra\s+|spare\s+)?(?:carrying case|protective case|"
        r"screen protector|memory card|tripod|ear pads|earpads|"
        r"watch strap|charger|charging cable|power adapter|"
        r"usb[ -]?c cable|lens cap)\b",
    )
    if any(re.search(pattern, title) for pattern in bundle_patterns):
        return "bundle"

    accessory_patterns = (
        r"\b(?:carrying case|protective case|phone case|tablet case|"
        r"laptop sleeve|screen protector|tempered glass|"
        r"replacement ear pads|replacement earpads|"
        r"replacement charger|charging cable|charging dock|"
        r"power adapter|usb[ -]?c cable|camera strap|watch strap|"
        r"lens cap|lens cover|battery case)\b",
        r"\b(?:replacement|spare)\s+(?:battery|charger|cable|"
        r"adapter|ear pads|earpads|strap|remote|lens cap)\b",
        r"\b(?:case|cover|sleeve|stand|mount|charger|adapter|"
        r"cable|protector)\s+(?:for|compatible with)\b",
    )
    if any(re.search(pattern, title) for pattern in accessory_patterns):
        return "accessory"

    return "product"


def is_accessory(record: Mapping[str, Any]) -> bool:
    """Recognize explicitly described standalone accessories."""
    return offer_kind(record) == "accessory"


def is_bundle(record: Mapping[str, Any]) -> bool:
    """Recognize explicitly described bundles and multi-packs."""
    return offer_kind(record) == "bundle"


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

    # Normalize identity fields once.
    ba, bb = compact(a.get("brand")), compact(b.get("brand"))
    ma, mb = compact(a.get("model")), compact(b.get("model"))
    va, vb = variant_map(a), variant_map(b)

    # Check contradictory title and structured storage information.
    if has_storage_conflict(a) or has_storage_conflict(b):
        return MatchResult(
            "uncertain",
            "Product title contradicts structured storage specification",
            "storage_data_conflict"
        )

    # Check contradictory title and structured RAM information.
    if has_ram_conflict(a) or has_ram_conflict(b):
        return MatchResult(
            "uncertain",
            "Product title contradicts structured RAM specification",
            "ram_data_conflict"
        )

    # Prevent accessories from being merged with main products.
    if is_accessory(a) != is_accessory(b):
        return MatchResult(
            "non_match",
            "Main product and accessory must not be merged",
            "product_type_conflict"
        )

    # Reject conflicting brands and models.
    # Bundles may include additional products that are not represented in variants.
    # Different offer types must not be grouped; even two bundles remain uncertain
    # until their contents can be compared through structured attributes.
    if is_bundle(a) != is_bundle(b):
        return MatchResult(
            "uncertain",
            "Bundle and standalone offer require separate review",
            "bundle_conflict"
        )
    if is_bundle(a) and is_bundle(b):
        return MatchResult(
            "uncertain",
            "Bundle contents are not independently verified",
            "bundle_contents_unverified"
        )

    if ba and bb and ba != bb:
        return MatchResult("non_match", "Brand differs", "brand")

    if ma and mb and ma != mb:
        return MatchResult("non_match", "Model differs", "model")

    # Reject conflicting variant attributes.
    for field in sorted(va.keys() & vb.keys()):
        if va[field] != vb[field]:
            return MatchResult(
                "non_match",
                f"Variant '{field}' differs",
                "variant_conflict"
            )

    # Normalize product identifiers.
    ga, gb = normalize_gtin(a.get("gtin")), normalize_gtin(b.get("gtin"))
    pa, pb = compact(a.get("mpn")), compact(b.get("mpn"))

    # Conflicting authoritative-looking identifiers require review.
    # MPN is only meaningful with an agreed brand.
    if ga and gb and ga != gb:
        return MatchResult(
            "uncertain",
            "Both valid GTINs differ; needs review",
            "gtin_conflict"
        )

    if ba and bb and pa and pb and pa != pb:
        return MatchResult(
            "uncertain",
            "Manufacturer part numbers differ",
            "mpn_conflict"
        )

    # Do not merge offers when a variant field is missing from one side.
    if va.keys() != vb.keys():
        return MatchResult(
            "uncertain",
            "Variant attributes are incomplete",
            "missing_variant"
        )


    # Match using validated GTIN.
    if ga and gb and ga == gb:
        return MatchResult(
            "match",
            "Validated GTIN matches with no observed conflicts",
            "gtin"
        )

    # Match using brand-scoped manufacturer part numbers.
    if ba and bb and ba == bb and pa and pb and pa == pb:
        return MatchResult(
            "match",
            "Brand and MPN match with no observed conflicts",
            "brand_mpn"
        )

    # Fallback when exact product identifiers are unavailable.
    # Require compatible brand and model.
    if not (ba and bb and ba == bb and ma and mb and ma == mb):
        return MatchResult(
            "uncertain",
            "Insufficient brand/model identity fields",
            "missing_identity"
        )

    # Require at least one identifying variant besides condition.
    if not (va.keys() - {"condition"}):
        return MatchResult(
            "uncertain",
            "No identifying variant attributes",
            "weak_attributes"
        )

    return MatchResult(
        "match",
        "Normalized brand, model and variants match",
        "attributes"
    )
