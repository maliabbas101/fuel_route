# USA boundary

`usa_boundary.geojson` is derived from the U.S. Census Bureau 2024 national
cartographic boundary at 1:5,000,000 scale (public domain / CC0).

Source: https://www2.census.gov/geo/tiger/GENZ2024/kml/cb_2024_us_nation_5m.zip
Documentation: https://www.census.gov/geographies/mapping-files/2024/geo/carto-boundary-file.html

Converted from KML polygons to a unioned WGS84 GeoJSON geometry, preserving holes.
Commit this file with the source so validation works without downloads or keys.
The dataset includes the fifty states, DC, Puerto Rico and mapped island areas.
Validation accepts points covered by this geometry, including polygon boundaries.
It validates endpoints, not whether the driving route stays within the country.

This is a generalized land/coastline boundary for an assessment prototype, not a
survey-grade border. Points near coastlines, borders or small islands can be
misclassified, so points within 1 km of the boundary are also accepted
(`USA_BOUNDARY_TOLERANCE_METERS`). This admits real coastal points such as Fort
Zachary Taylor in Key West, but also points within 1 km across the Mexican or
Canadian border.
