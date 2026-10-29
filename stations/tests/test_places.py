from django.test import SimpleTestCase

from stations.places import census_keys, miles_between, place_key


class PlaceKeyTests(SimpleTestCase):
    def test_spelling_variants_share_a_key(self):
        for a, b in (
            ("Saint Johns", "St. Johns"),
            ("Mc Calla", "McCalla"),
            ("De Forest", "DeForest"),
            ("Fort Worth", "Ft Worth"),
            ("Mount Vernon", "Mt. Vernon"),
        ):
            with self.subTest(a=a, b=b):
                self.assertEqual(place_key(a), place_key(b))


class CensusKeysTests(SimpleTestCase):
    def test_legal_suffixes_and_prefixes_are_removed(self):
        self.assertIn(place_key("Tomah"), census_keys("Tomah city"))
        self.assertIn(place_key("Pecos"), census_keys("Town of Pecos city"))

    def test_full_name_is_kept_when_it_ends_like_a_suffix(self):
        self.assertIn(place_key("Carson City"), census_keys("Carson City"))
        self.assertIn(place_key("Boise City"), census_keys("Boise City city"))

    def test_consolidated_city_matches_its_first_name(self):
        keys = census_keys("Nashville-Davidson metropolitan government (balance)")
        self.assertIn(place_key("Nashville"), keys)


class MilesBetweenTests(SimpleTestCase):
    def test_new_york_to_los_angeles(self):
        miles = miles_between((40.7128, -74.0060), (34.0522, -118.2437))
        self.assertAlmostEqual(miles, 2451, delta=5)
