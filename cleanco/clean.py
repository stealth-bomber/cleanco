"""Functions to help clean & normalize business names.

See http://www.unicode.org/reports/tr15/#Normalization_Forms_Table for details
on Unicode normalization and the NFKD normalization used here.

Basic usage:

>> terms = prepare_default_terms()
>> basename("Daddy & Sons, Ltd.", terms, prefix=True, middle=True, suffix=True)
Daddy & Sons

"""

import functools
import operator
import re
import unicodedata
from typing import Generator, List, Optional, Set, Tuple

from .non_nfkd_map import NON_NFKD_MAP
from .termdata import (
    country_codes,
    country_name_by_country,
    global_terms,
    terms_by_country,
    terms_by_type,
)

# Constants
MIN_GROUP_NAME_LENGTH = 5
OSUUSKUNTA_PLACEHOLDER = "OSUUSKUNTA_PLACEHOLDER"
COUNTRY_PREPOSITIONS = ["in", "of"]
SWEDISH_INDICATORS = ["föreningen", "förening", "kosmetolog"]
BILINGUAL_SEPARATORS = [",", ";", " - ", " – "]

# Compiled regex patterns
tail_removal_rexp = re.compile(r"[^\.\w]+$", flags=re.UNICODE)
parenthesis_removal_rexp = re.compile(r"\s*\(.*\)\s*")

# Patterns for Finnish branch-related phrases (case-insensitive)
finnish_branch_patterns = [
    # Patterns with slashes (must come first to match before simpler patterns)
    re.compile(r",\s*filial\s+i\s+finland\s*/\s*suomen\s+sivuliike", re.IGNORECASE),
    re.compile(
        r",\s*sivuliike\s+helsingissä\s*/\s*helsinki\s+branch.*$", re.IGNORECASE
    ),
    re.compile(r",\s*filial\s+i\s+finland\s*/\s*suomen\s+sivuliike.*$", re.IGNORECASE),
    # Patterns with dashes
    re.compile(r",\s*sivuliike\s+suomessa\s*-\s*filial\s+i\s+finland", re.IGNORECASE),
    re.compile(r"\s+sivuliike\s+suomessa\s*-\s*filial\s+i\s+finland", re.IGNORECASE),
    # "- filial Finland" pattern (with nested parentheses)
    re.compile(r"\s*-\s*filial\s+finland\s*\(.*?\)\s*$", re.IGNORECASE),
    re.compile(r"\s*-\s*filial\s+finland\s*$", re.IGNORECASE),
    # "filial i Finland" (Swedish)
    re.compile(r",\s*filial\s+i\s+finland", re.IGNORECASE),
    re.compile(r"\s+filial\s+i\s+finland", re.IGNORECASE),
    # "filial" (Swedish, standalone after comma or space)
    re.compile(r",\s*filial\s*$", re.IGNORECASE),
    re.compile(r"\s+filial\s*$", re.IGNORECASE),
    # "Filialen" (Swedish, "the branch")
    re.compile(r"^filialen\s+", re.IGNORECASE),
    # "sivuliike Suomessa" (Finnish)
    re.compile(r",\s*sivuliike\s+suomessa", re.IGNORECASE),
    re.compile(r"\s+sivuliike\s+suomessa", re.IGNORECASE),
    # "Suomi sivuliike" (Finnish - different word order)
    re.compile(r",\s*suomi\s+sivuliike", re.IGNORECASE),
    re.compile(r"\s+suomi\s+sivuliike", re.IGNORECASE),
    # "Suomen sivuliike" (Finnish)
    re.compile(r",\s*suomen\s+sivuliike", re.IGNORECASE),
    re.compile(r"\s+suomen\s+sivuliike", re.IGNORECASE),
    # "Suomen Sivuliike" (capitalized)
    re.compile(r"\s+suomen\s+sivuliike\s*$", re.IGNORECASE),
    # "Helsingin sivuliike" (Finnish)
    re.compile(r",\s*helsingin\s+sivuliike", re.IGNORECASE),
    re.compile(r"\s+helsingin\s+sivuliike", re.IGNORECASE),
    # "Sivuliike Helsingissä" (Finnish)
    re.compile(r",\s*sivuliike\s+helsingissä", re.IGNORECASE),
    re.compile(r"\s+sivuliike\s+helsingissä", re.IGNORECASE),
]


def get_unique_terms(country: Optional[str] = None) -> Set[str]:
    """Retrieve all unique terms from termdata definitions.

    Args:
        country: Optional country code to filter terms by country.

    Returns:
        Set of unique terms, optionally filtered by country.
    """
    if country in terms_by_country:
        return set(terms_by_country[country]).union(global_terms)

    type_terms = functools.reduce(operator.iconcat, terms_by_type.values(), [])
    country_terms = functools.reduce(operator.iconcat, terms_by_country.values(), [])
    country_name_terms = functools.reduce(
        operator.iconcat, country_name_by_country.values(), []
    )
    return set(type_terms + country_terms + country_name_terms)


def remove_accents(text: str) -> str:
    """Remove accents and diacritics from text using NFKD normalization.

    Based on https://stackoverflow.com/a/51230541

    Args:
        text: Input text to remove accents from.

    Returns:
        Text with accents removed.
    """
    nfkd_form = unicodedata.normalize("NFKD", text.casefold())
    return "".join(
        NON_NFKD_MAP[c] if c in NON_NFKD_MAP else c
        for part in nfkd_form
        for c in part
        if unicodedata.category(part) != "Mn"
    )


def strip_punct(text: str) -> str:
    """Remove punctuation characters from text.

    Args:
        text: Input text to strip punctuation from.

    Returns:
        Text with punctuation removed.
    """
    return text.replace(".", "").replace(",", "").replace("-", "")


def normalize_terms(terms: Set[str]) -> Generator[str, None, None]:
    """Normalize terms by removing accents and punctuation.

    Args:
        terms: Set of terms to normalize.

    Returns:
        Generator of normalized terms.
    """
    return (strip_punct(remove_accents(term)) for term in terms)


def strip_tail(name: str) -> str:
    """Remove trailing non-letter symbols except dot and closing parenthesis.

    Args:
        name: Input name to strip tail from.

    Returns:
        Name with trailing symbols removed.
    """
    match = re.search(tail_removal_rexp, name)
    if match is not None:
        name = name[: match.span()[0]]
    return name


def normalized(text: str) -> str:
    """Perform caseless Unicode normalization.

    Args:
        text: Input text to normalize.

    Returns:
        Normalized text with accents removed.
    """
    return remove_accents(text)


def split_bilingual_name(name: str) -> str:
    """Split bilingual Finnish-Swedish company names and return the Finnish part.

    Handles cases where the same company name appears in both Finnish and Swedish,
    separated by comma, semicolon, or dash. Finnish-Swedish legal form pairs:
    - ry (Finnish) / rf (Swedish) - registered association
    - sr (Finnish) / sr (Swedish) - foundation
    - s.r. (Finnish) / s.r. (Swedish) - foundation
    - r.y. (Finnish) / r.f. (Swedish) - registered association
    - Oy (Finnish) / Ab (Swedish) - limited company

    Returns the Finnish part if both forms are detected, otherwise returns original name.
    """
    # Quick check: if name doesn't contain any Finnish/Swedish indicators, return early
    name_lower = name.lower()
    # Check for any Finnish/Swedish legal forms or indicators
    finnish_swedish_indicators = [
        " ry",
        " rf",
        " r.y.",
        " r.f.",
        " oy",
        " ab",
        " oyj",
        "osuuskunta",
        "andelslag",
        " co-op",
        " coop",
        "finska",
        "ruotsiksi",
        "i finland",
    ]
    if not any(indicator in name_lower for indicator in finnish_swedish_indicators):
        return name

    # Check for distinct pairs (ry/rf, r.y./r.f., oy/ab)
    has_ry = " ry" in name_lower or name_lower.endswith(" ry")
    has_rf = " rf" in name_lower or name_lower.endswith(" rf")
    has_ry_pair = has_ry and has_rf

    has_r_y = " r.y." in name_lower or name_lower.endswith(" r.y.")
    has_r_f = " r.f." in name_lower or name_lower.endswith(" r.f.")
    has_r_y_pair = has_r_y and has_r_f

    has_oy = " oy" in name_lower or name_lower.endswith(" oy") or " oyj" in name_lower
    has_ab = " ab" in name_lower or name_lower.endswith(" ab")
    has_oy_pair = has_oy and has_ab

    has_osuuskunta = " osuuskunta" in name_lower or name_lower.startswith("osuuskunta ")
    has_andelslag = " andelslag" in name_lower or name_lower.endswith(" andelslag")
    has_coop = (
        " co-op" in name_lower
        or name_lower.endswith(" co-op")
        or " coop" in name_lower
        or name_lower.endswith(" coop")
    )
    has_osuuskunta_pair = has_osuuskunta and (has_andelslag or has_coop)

    # If we detect bilingual pairs, try to split
    if has_ry_pair or has_r_y_pair or has_oy_pair or has_osuuskunta_pair:
        # Try splitting on common separators: comma, semicolon, dash
        for sep in BILINGUAL_SEPARATORS:
            if sep in name:
                parts = name.split(sep, 1)
                if len(parts) == 2:
                    first_part = parts[0].strip()
                    second_part = parts[1].strip()

                    # Check if first part has Finnish form and second has Swedish form
                    first_lower = first_part.lower()
                    second_lower = second_part.lower()

                    # Check for specific pairs
                    if has_ry_pair and (
                        (" ry" in first_lower or first_lower.endswith(" ry"))
                        and (" rf" in second_lower or second_lower.endswith(" rf"))
                    ):
                        return first_part

                    if has_r_y_pair and (
                        (" r.y." in first_lower or first_lower.endswith(" r.y."))
                        and (" r.f." in second_lower or second_lower.endswith(" r.f."))
                    ):
                        return first_part

                    if has_oy_pair and (
                        (
                            " oy" in first_lower
                            or first_lower.endswith(" oy")
                            or " oyj" in first_lower
                        )
                        and (" ab" in second_lower or second_lower.endswith(" ab"))
                    ):
                        return first_part

                    if has_osuuskunta_pair and (
                        ("osuuskunta" in first_lower)
                        and (
                            ("andelslag" in second_lower)
                            or (
                                " co-op" in second_lower
                                or second_lower.endswith(" co-op")
                            )
                            or (
                                " coop" in second_lower
                                or second_lower.endswith(" coop")
                            )
                        )
                    ):
                        return first_part

    # Also handle cases where there's a dash separator and the second part contains Swedish words
    # followed by "i Finland" and ends with "ry" (e.g., "X - Y i Finland ry")
    if " - " in name or " – " in name:
        for sep in BILINGUAL_SEPARATORS[2:]:  # Only dash separators
            if sep in name:
                parts = name.split(sep, 1)
                if len(parts) == 2:
                    second_part = parts[1].strip().lower()
                    # Check if second part contains Swedish words (like "Kosmetologföreningen")
                    # and "i finland" and ends with "ry"
                    if "i finland" in second_part and second_part.endswith(" ry"):
                        # Check if second part contains Swedish-looking words
                        if any(
                            indicator in second_part for indicator in SWEDISH_INDICATORS
                        ):
                            return parts[0].strip()

        # Handle space-separated bilingual names (e.g., "X ry Finska Y rf")
        # Look for pattern: Finnish form, then Swedish word (like "Finska"), then Swedish form
        if has_ry_pair:
            # Find the position of " rf" (Swedish form)
            rf_pos = name_lower.rfind(" rf")
            if rf_pos > 0:
                # Look backwards for " ry" (Finnish form)
                ry_pos = name_lower.rfind(" ry", 0, rf_pos)
                if ry_pos > 0:
                    # Check if there's a Swedish indicator word like "Finska" between them
                    middle_part = name_lower[ry_pos + 3 : rf_pos].strip()
                    # If middle part starts with Swedish words (Finska, Finska Vikens, etc.)
                    if (
                        middle_part.startswith("finska")
                        or "finska" in middle_part.split()[:2]
                    ):
                        # Return everything up to and including " ry"
                        return name[: ry_pos + 3].strip()
            # Also handle "X ry Finska Y rf" pattern where "Finska" comes after "ry"
            # Check if there's "ry" followed by "Finska" followed by "rf"
            ry_finska_rf_pattern = re.search(r"\bry\s+.*?finska.*?\s+rf\b", name_lower)
            if ry_finska_rf_pattern:
                # Find the "ry" position
                ry_pos = name_lower.find(" ry")
                if ry_pos >= 0:
                    return name[: ry_pos + 3].strip()

        if has_r_y_pair:
            # Similar logic for r.y./r.f. pair
            r_f_pos = name_lower.rfind(" r.f.")
            if r_f_pos > 0:
                r_y_pos = name_lower.rfind(" r.y.", 0, r_f_pos)
                if r_y_pos > 0:
                    middle_part = name_lower[r_y_pos + 5 : r_f_pos].strip()
                    if (
                        middle_part.startswith("finska")
                        or "finska" in middle_part.split()[:2]
                    ):
                        return name[: r_y_pos + 5].strip()
            # Also handle "X r.y. ruotsiksi Y r.f." pattern
            # "ruotsiksi" means "in Swedish" and indicates bilingual content
            ruotsiksi_pattern = re.search(
                r"\br\.y\.\s+.*?ruotsiksi.*?\s+r\.f\.\b", name_lower
            )
            if ruotsiksi_pattern:
                r_y_pos = name_lower.find(" r.y.")
                if r_y_pos >= 0:
                    return name[: r_y_pos + 5].strip()

    # Handle additional bilingual patterns that might not have been caught above
    # Pattern: "X ry Finska Y rf" - check if "ry" is followed by "Finska" and then "rf"
    if " ry" in name_lower and " rf" in name_lower and "finska" in name_lower:
        ry_finska_rf_pattern = re.search(r"\bry\s+.*?finska.*?\s+rf\b", name_lower)
        if ry_finska_rf_pattern:
            ry_pos = name_lower.find(" ry")
            if ry_pos >= 0:
                return name[: ry_pos + 3].strip()

    # Pattern: "X r.y. ruotsiksi Y r.f." - "ruotsiksi" means "in Swedish"
    if " r.y." in name_lower and " r.f." in name_lower and "ruotsiksi" in name_lower:
        # Find positions
        r_y_pos = name_lower.find(" r.y.")
        r_f_pos = name_lower.find(" r.f.")
        ruotsiksi_pos = name_lower.find("ruotsiksi")
        # Check if "ruotsiksi" comes after "r.y." and before "r.f."
        if (
            r_y_pos >= 0
            and r_f_pos > r_y_pos
            and ruotsiksi_pos > r_y_pos
            and ruotsiksi_pos < r_f_pos
        ):
            return name[: r_y_pos + 5].strip()

    return name


def handle_finnish_insurance_companies(name: str) -> Tuple[str, bool]:
    """Handle Finnish mutual insurance company names.

    Patterns:
    - "Keskinäinen [insurance terms] CompanyName" -> "CompanyName"
    - "CompanyName Keskinäinen Vakuutusyhtiö" -> "CompanyName" (unless first word ends with "n" - genitive)

    Returns tuple of (cleaned_name, is_genitive_case) where is_genitive_case indicates
    if the name should be protected from further term removal.
    """
    # Quick check: if name doesn't contain "keskinäinen", return early
    name_lower = name.lower()
    if "keskinäinen" not in name_lower:
        return (name, False)

    # Pattern 1: "Keskinäinen [insurance terms] CompanyName"
    # Extract company name that comes after insurance terms
    keskinainen_pattern = re.compile(
        r"^keskinäinen\s+(työeläkevakuutusyhtiö|eläkevakuutusyhtiö|vakuutusyhtiö)\s+(.+)$",
        re.IGNORECASE,
    )
    match = keskinainen_pattern.match(name)
    if match:
        company_name = match.group(2).strip()
        return (company_name, False)

    # Pattern 2: "CompanyName Keskinäinen Vakuutusyhtiö"
    # Extract company name that comes before, unless first word ends with "n" (genitive case)
    keskinainen_end_pattern = re.compile(
        r"^(.+?)\s+keskinäinen\s+vakuutusyhtiö\s*$", re.IGNORECASE
    )
    match = keskinainen_end_pattern.match(name)
    if match:
        company_name = match.group(1).strip()
        # Check if first word ends with "n" (genitive case in Finnish)
        first_word = company_name.split()[0] if company_name.split() else ""
        if first_word and first_word.endswith("n"):
            # Genitive case - keep the full name as is and mark as protected
            return (name, True)
        return (company_name, False)

    return (name, False)


def remove_finnish_branch_patterns(name: str) -> str:
    """Remove Finnish branch-related phrases from company names.

    Handles patterns like:
    - "filial i Finland" (Swedish)
    - "sivuliike Suomessa" (Finnish)
    - "Suomen sivuliike" (Finnish)
    - "Helsingin sivuliike" (Finnish)
    - Mixed patterns with slashes and dashes

    Also handles comma-separated variants where the last part is a branch pattern.
    In such cases, takes the first part before the comma-separated variant.
    """
    # Quick check: if name doesn't contain any Finnish branch indicators, return early
    name_lower = name.lower()
    branch_indicators = [
        "filial",
        "sivuliike",
        "suomen",
        "helsingin",
        "helsingissä",
        "suomessa",
        "suomi",
    ]
    if not any(indicator in name_lower for indicator in branch_indicators):
        return name

    result = name

    # Check if any branch pattern matches
    matched = False
    for pattern in finnish_branch_patterns:
        if pattern.search(result):
            matched = True
            result = pattern.sub("", result)
            break  # Only apply first matching pattern

    # If we matched a branch pattern and there are multiple comma-separated parts,
    # take the first part (assuming it's the main company name)
    if matched:
        # Clean up any trailing commas, spaces, dashes, or slashes left after removal
        result = re.sub(r"[,\s/-]+$", "", result)
        result = re.sub(r",\s*,", ",", result)  # Remove double commas

        # Remove any trailing text after slashes (e.g., "/ Helsinki Branch")
        result = re.sub(r"/.*$", "", result)
        result = result.strip()

        # If there are still multiple comma-separated parts, take the first one
        # This handles cases like "Nordisk Kellogg Finland, Nordisk Kellogg ApS"
        parts = [p.strip() for p in result.split(",") if p.strip()]
        if len(parts) > 1:
            # Check if parts look like variants (e.g., "X Y, X Z")
            # If so, take the first part
            first_words = set(parts[0].split()[:2])  # First 2 words of first part
            if any(
                len(set(p.split()[:2]).intersection(first_words)) > 0 for p in parts[1:]
            ):
                result = parts[0]
            else:
                # If not clearly variants, still take first part if branch was removed
                result = parts[0]

        result = result.strip()

        # Remove regional qualifiers like "Nordic" when they appear before a legal form and branch was removed
        # Pattern: "X Technologies Nordic AB" -> "X Technologies" (after AB is removed by suffix removal)
        # This handles cases where "Nordic" is a regional qualifier for a branch
        # We check if "Nordic" is followed by common legal forms
        result = re.sub(r"\s+nordic\s*$", "", result, flags=re.IGNORECASE)
        result = result.strip()

    return result


def prepare_default_terms(
    country: Optional[str] = None,
) -> List[Tuple[int, List[str]]]:
    """Construct an optimized term structure for basename extraction.

    Terms are sorted deterministically: descending by number of tokens,
    ascending by names.

    Args:
        country: Optional country code to filter terms.

    Returns:
        List of tuples (term_length, term_parts) sorted for optimal matching.
    """
    terms = get_unique_terms(country)
    normalized_term_list = normalize_terms(terms)
    term_parts_list = (term.split() for term in normalized_term_list)
    # Make sure that the result is deterministic, sort terms descending by
    # number of tokens, ascending by names
    sorted_term_parts = sorted(term_parts_list, key=lambda x: (-len(x), x))
    return [(len(term_parts), term_parts) for term_parts in sorted_term_parts]


def _get_all_country_names() -> List[str]:
    """Get all country names from termdata.

    Returns:
        List of all country names.
    """
    return functools.reduce(operator.iconcat, country_name_by_country.values(), [])


def _is_finnish_country(country: Optional[str]) -> Optional[bool]:
    """Check if the country parameter indicates Finland.

    Args:
        country: Country code (e.g. "FI") or country name (e.g. "Finland").

    Returns:
        True if country is Finland, False if it's explicitly not Finland,
        None if country is not specified (unknown - should check for indicators).
    """
    if country is None:
        return None  # Unknown - should check for indicators
    country_normalized = country_codes.get(country, country)
    return country_normalized == "Finland"


def custom_basename(
    name: str,
    terms: List[Tuple[int, List[str]]],
    suffix: bool = True,
    prefix: bool = False,
    middle: bool = False,
    country_names: List[str] = None,
    **kwargs,
) -> str:
    """Return cleaned base version of the business name.

    Args:
        name: Business name to clean.
        terms: List of tuples (term_length, term_parts) for matching.
        suffix: Whether to remove suffixes.
        prefix: Whether to remove prefixes.
        middle: Whether to remove middle terms.
        country_names: Optional list of country names to remove.
        **kwargs: Additional keyword arguments (ignored).

    Returns:
        Cleaned base name.
    """
    if country_names is None:
        country_names = []

    name = strip_tail(name)
    name_parts = name.split()
    normalized_name = normalized(name)
    normalized_parts = list(map(strip_punct, normalized_name.split()))
    normalized_size = len(normalized_parts)

    all_country_names = _get_all_country_names()
    # Pre-compute lowercase country names set for faster lookups
    all_country_names_lower = {cn.lower() for cn in all_country_names}

    if suffix:
        for term_size, term_parts in terms:
            if normalized_parts[-term_size:] == term_parts:
                # Don't remove if it's a country name preceded by "in" or "of"
                if (
                    term_size == 1
                    and term_parts[0].lower() in all_country_names_lower
                    and len(name_parts) >= 2
                    and name_parts[-2].lower() in COUNTRY_PREPOSITIONS
                ):
                    continue  # Preserve country name after "in" or "of"
                del normalized_parts[-term_size:]
                del name_parts[-term_size:]

    if prefix:
        for term_size, term_parts in terms:
            if normalized_parts[:term_size] == term_parts:
                # Don't remove country names as prefixes - they should only be removed as suffixes
                # Country names are typically qualifiers at the end, not prefixes
                # This prevents removing "Suomi" from "Suomi Teline" etc.
                if term_size == 1 and term_parts[0].lower() in all_country_names_lower:
                    continue
                del normalized_parts[:term_size]
                del name_parts[:term_size]

    if middle:
        for term_size, term_parts in terms:
            if term_size > 1:
                size_diff = normalized_size - term_size
                if size_diff > 1:
                    for i in range(0, normalized_size - term_size + 1):
                        if term_parts == normalized_parts[i : i + term_size]:
                            del normalized_parts[i : i + term_size]
                            del name_parts[i : i + term_size]
            else:
                if term_parts[0] in normalized_parts[1:-1]:
                    idx = normalized_parts[1:-1].index(term_parts[0])
                    del normalized_parts[idx + 1]
                    del name_parts[idx + 1]

    for country_name in country_names:
        if name_parts and name_parts[-1].lower() == country_name.lower():
            # In specific cases (e.g. "XXX of Sweden" or "XXX in Finland"),
            # we should leave the country name
            if len(name_parts) >= 2 and name_parts[-2].lower() in COUNTRY_PREPOSITIONS:
                continue

            normalized_parts = normalized_parts[:-1]
            name_parts = name_parts[:-1]

    return strip_tail(" ".join(name_parts))


def basename(
    name: str,
    suffix: bool = True,
    prefix: bool = True,
    middle: bool = False,
    country: Optional[str] = None,
) -> str:
    """
    Cleans the business names
    Convenience for most common use cases that don't parametrize base name extraction
    Inputs:
        name: business name
        suffix: whether to remove suffixes
        prefix: whether to remove prefixes
        middle: whether to remove middle terms
        country: country code (e.g. FI) or country name (e.g. Finland)
    Returns:
        cleaned base version of the business name
    """
    # Check if we should run Finnish-specific logic
    # If country is explicitly "FI" or "Finland", run Finnish checks
    # If country is None (unknown), we'll check for indicators in the name
    # If country is explicitly non-Finnish, skip Finnish checks
    is_finnish_explicit = country == "FI" or country == "Finland"
    is_non_finnish_explicit = country is not None and not is_finnish_explicit

    # Handle Finnish insurance company names (only if Finnish or unknown)
    protect_osuuskunta = False
    name_lower = name.lower()

    if not is_non_finnish_explicit:  # Finnish or unknown (None)
        name, is_genitive_case = handle_finnish_insurance_companies(name)

        # If genitive case, return early to preserve the insurance terms
        if is_genitive_case:
            return name.strip()

        # Check for genitive case with "Osuuskunta" (e.g., "Helsingin Festivaaliorkesterin Osuuskunta")
        # If the word before "Osuuskunta" ends with "n", preserve "Osuuskunta"
        if "osuuskunta" in name_lower:
            osuuskunta_match = re.search(r"\b(\w+)\s+osuuskunta\b", name, re.IGNORECASE)
            if osuuskunta_match:
                preceding_word = osuuskunta_match.group(1)
                if preceding_word.endswith("n"):
                    # Genitive case - protect "Osuuskunta" from removal
                    protect_osuuskunta = True

        # Split bilingual names (Finnish-Swedish pairs)
        name = split_bilingual_name(name)
        # Update name_lower after bilingual split
        name_lower = name.lower()
    else:
        # Not Finnish - skip Finnish-specific checks entirely
        pass

    # Check if "Group" appears immediately before a company form in the original name
    # This check happens before branch pattern removal to see the original structure
    group_before_company_form = False
    if " group " in name_lower or name_lower.endswith(" group"):
        # Get all company form terms to check if Group is immediately followed by one
        all_terms = get_unique_terms(country_codes.get(country, country))
        # Check if Group is immediately followed by any company form term
        # Pattern: "Group" followed by optional punctuation/whitespace, then company form
        group_match = re.search(r"\s+group\s*([.,\s-]*)", name_lower)
        if group_match:
            after_group_start = group_match.end()
            after_group = name_lower[after_group_start:].strip()
            # Check if what immediately follows Group (after optional punctuation) is a company form
            # Remove leading punctuation/whitespace for comparison
            after_group_clean = re.sub(r"^[.,\s-]+", "", after_group)
            for term in all_terms:
                term_lower = term.lower().strip()
                # Check if the term matches the start of what's after Group
                if after_group_clean.startswith(term_lower):
                    group_before_company_form = True
                    break

    # Remove Finnish branch patterns and check if any were matched
    # Only run if Finnish or unknown (not explicitly non-Finnish)
    original_name = name
    if not is_non_finnish_explicit:  # Finnish or unknown (None)
        name = remove_finnish_branch_patterns(name)
    branch_pattern_matched = name != original_name

    no_parenthesis = parenthesis_removal_rexp.sub(" ", name).strip()
    country_name = country_codes.get(country, country)
    terms = prepare_default_terms(country_name)
    # Get country names - if no specific country, use all country names to preserve
    # "in Finland" patterns
    if country_name:
        country_names = country_name_by_country.get(country_name, [])
    else:
        # When no country specified, use all country names to handle cases like
        # "X in Finland"
        country_names = _get_all_country_names()

    # Protect "Osuuskunta" in genitive cases
    protected_name = no_parenthesis
    if protect_osuuskunta:
        # Replace "Osuuskunta" with a placeholder
        protected_name = re.sub(
            r"\bosuuskunta\b",
            OSUUSKUNTA_PLACEHOLDER,
            protected_name,
            flags=re.IGNORECASE,
        )

    # Run cleaning twice to catch nested terms (e.g., "Company Ltd Oy" -> "Company")
    cleaned_name = custom_basename(
        protected_name,
        terms,
        suffix=suffix,
        prefix=prefix,
        middle=middle,
        country_names=country_names,
    )
    # Only run second pass if first pass made changes
    if cleaned_name != protected_name:
        cleaned_name = custom_basename(
            cleaned_name,
            terms,
            suffix=suffix,
            prefix=prefix,
            middle=middle,
            country_names=country_names,
        )

    # Avoid cases where the name is stripped from all its words
    if not cleaned_name:
        return name

    # Post-processing: Remove regional qualifiers like "Nordic" when branch pattern was present
    # This handles cases like "Infineon Technologies Nordic AB, filial" -> "Infineon Technologies"
    # But preserve "Nordic" when it's part of the brand name (e.g., "LG Electronics Nordic")
    if branch_pattern_matched:
        # Only remove "Nordic" if it's preceded by "Technologies"
        # (common pattern for regional qualifiers)
        # This preserves "Nordic" in brand names like "LG Electronics Nordic"
        cleaned_name = re.sub(
            r"\s+technologies\s+nordic\s*$",
            " Technologies",
            cleaned_name,
            flags=re.IGNORECASE,
        ).strip()

    # Post-processing: Remove "Group" only if:
    # 1. It was before a company form in the original name (checked before branch removal)
    # 2. Exception: Don't drop "Group" if total length of meaningful words < 5 chars
    # This preserves:
    # - "ME Group" -> "ME Group" (ME is < 5 chars, even though Group is before company form)
    # But removes Group from:
    # - "Anora Group Oyj" -> "Anora" (single word >= 5 chars, Group before Oyj)
    # - "Enity Bank Group AB" -> "Enity Bank" (multiple words, Group before AB)
    if group_before_company_form:
        cleaned_name = _remove_group_if_safe(cleaned_name)

    # Restore "Osuuskunta" for genitive cases
    if protect_osuuskunta:
        cleaned_name = _restore_osuuskunta(cleaned_name, original_name)

    return cleaned_name


def _remove_group_if_safe(name: str) -> str:
    """Remove "Group" from name if safe to do so.

    Keeps "Group" if total length of meaningful words before it is < 5 chars.
    This preserves short names like "ME Group" or "G - J Group".

    Args:
        name: Name potentially containing "Group".

    Returns:
        Name with "Group" removed if safe, otherwise original name.
    """

    def remove_group_if_safe_callback(match):
        before_group = match.group(1).strip()
        words = before_group.split()
        # Calculate total length of meaningful words (excluding punctuation-only words)
        total_length = 0
        for word in words:
            # Remove trailing dashes/punctuation for length calculation
            clean_word = re.sub(r"[-–—]$", "", word).strip()
            # Skip punctuation-only words (like "-")
            if clean_word and not re.match(r"^[-–—]+$", clean_word):
                total_length += len(clean_word)

        # Exception: Keep Group if total length of meaningful words < 5 chars
        # This handles cases like "G - J Group" (G + J = 2 chars) or "ME Group" (ME = 2 chars)
        if total_length < MIN_GROUP_NAME_LENGTH:
            # Short words - keep Group (e.g., "ME Group", "HL Group", "G - J Group")
            return match.group(0)
        # Total length >= 5 chars - safe to remove Group
        return before_group

    return re.sub(
        r"^(.+?)\s+group\s*$",
        remove_group_if_safe_callback,
        name,
        flags=re.IGNORECASE,
    )


def _restore_osuuskunta(cleaned_name: str, original_name: str) -> str:
    """Restore "Osuuskunta" from placeholder using original capitalization.

    Args:
        cleaned_name: Name with OSUUSKUNTA_PLACEHOLDER.
        original_name: Original name to extract capitalization from.

    Returns:
        Name with placeholder replaced by original form.
    """
    original_osuuskunta_match = re.search(
        r"\bosuuskunta\b", original_name, re.IGNORECASE
    )
    original_osuuskunta_form = (
        original_osuuskunta_match.group(0)
        if original_osuuskunta_match
        else "Osuuskunta"
    )
    return re.sub(
        rf"\b{re.escape(OSUUSKUNTA_PLACEHOLDER)}\b",
        original_osuuskunta_form,
        cleaned_name,
        flags=re.IGNORECASE,
    )
