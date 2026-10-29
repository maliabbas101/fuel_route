USA_STATES = frozenset(
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN "
    "MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA "
    "WV WI WY".split()
)

PLACE_SOURCES = ("census_place", "census_cousub", "geonames")
AMBIGUITY_MILES = 25
GEONAMES_SKIPPED_CODES = frozenset({"PPLQ", "PPLH", "PPLW", "PPLCH"})
METERS_PER_MILE = 1609.344

DEFAULT_PLACE_COORDINATES = "data/place-coordinates.csv"
DEFAULT_STATION_COORDINATES = "data/station-coordinates.csv"
