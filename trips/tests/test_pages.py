from django.test import TestCase
from django.urls import reverse


class PageTests(TestCase):
    def test_home_page_links_to_the_map_and_api(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("trip-map"))
        self.assertContains(response, reverse("plan-trip"))
        self.assertContains(response, "500 miles of range")

    def test_map_page_loads(self):
        response = self.client.get(reverse("trip-map"))

        self.assertEqual(response.status_code, 200)
