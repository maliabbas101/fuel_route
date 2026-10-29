"""City-name matching shared by the place-coordinate commands."""

import re

USA_STATES = frozenset(
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN "
    "MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA "
    "WV WI WY".split()
)

# Census names carry a legal suffix: "Tomah city", "Big Cabin town".
CENSUS_SUFFIX = re.compile(
    r"\s+(city and borough|(consolidated|metropolitan|unified) government"
    r"|urban county|charter township|city|town|township|village|borough|CDP"
    r"|municipality|plantation|gore|grant|location|purchase"
    r"|unorganized territory)$",
    re.IGNORECASE,
)
# Example: "Town of Pecos city".
CENSUS_PREFIX = re.compile(r"^(town|city|village|borough) of\s+", re.IGNORECASE)


def place_key(name):
    """Normalize "Saint Johns", "St. Johns" and "ST JOHNS" to one key."""
    name = name.upper().replace(".", "").replace("'", "")
    name = re.sub(r"\b(SAINTE|SAINT|STE|ST)\b", "ST", name)
    name = re.sub(r"\b(FORT|FT)\b", "FT", name)
    name = re.sub(r"\b(MOUNT|MT)\b", "MT", name)
    # Dropping spaces also joins "Mc Calla" and "De Forest".
    return re.sub(r"[^A-Z0-9]", "", name)


def census_keys(name):
    # Example: "Nashville-Davidson metropolitan government (balance)".
    full = re.sub(r"\s*\(.*?\)", "", name.strip())
    base = CENSUS_PREFIX.sub("", CENSUS_SUFFIX.sub("", full))
    names = {full, base}
    if "-" in base:
        names.add(base.split("-")[0])
    return {place_key(value) for value in names}
