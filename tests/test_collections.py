import unittest

from src.collections import (
    DEFAULT_MOUNT_FACTIONS,
    calculate_mounts,
    calculate_pets,
    filter_by_faction,
    normalize_mount_catalog,
    normalize_owned_mounts,
    normalize_owned_pets,
    normalize_pet_catalog,
)


class CollectionsTests(unittest.TestCase):
    def test_owned_mount_matching_and_missing_calculation(self):
        owned = {"mounts": [{"mount": {"id": 1, "name": "Swift Horse"}}]}
        catalog = {
            "mounts": [
                {"id": 1, "name": "Swift Horse"},
                {"id": 2, "name": "Armored Wolf"},
            ]
        }

        result = calculate_mounts(owned, catalog)

        self.assertEqual([record["id"] for record in result["owned"]], [1])
        self.assertEqual([record["id"] for record in result["missing"]], [2])

    def test_owned_pet_matching_and_missing_calculation(self):
        owned = {"pets": [{"species": {"id": 10, "name": "Cat"}}]}
        catalog = {
            "pets": [
                {"id": 10, "name": "Cat"},
                {"id": 11, "name": "Dog"},
            ]
        }

        result = calculate_pets(owned, catalog)

        self.assertEqual([record["id"] for record in result["owned"]], [10])
        self.assertEqual([record["id"] for record in result["missing"]], [11])

    def test_alliance_neutral_filter_keeps_unknown_and_excludes_horde(self):
        records = normalize_mount_catalog({
            "mounts": [
                {"id": 1, "name": "Alliance", "faction": {"type": "ALLIANCE"}},
                {"id": 2, "name": "Horde", "faction": {"name": "Horde"}},
                {"id": 3, "name": "Neutral", "faction": "Neutral"},
                {"id": 4, "name": "Unknown"},
            ]
        })

        filtered = filter_by_faction(records, DEFAULT_MOUNT_FACTIONS)

        self.assertEqual([record["id"] for record in filtered], [1, 3, 4])

    def test_alliance_focused_comparison_filters_owned_horde_records(self):
        result = calculate_mounts(
            {
                "mounts": [
                    {"id": 1, "name": "Alliance", "faction": "Alliance"},
                    {"id": 2, "name": "Horde", "faction": "Horde"},
                ]
            },
            {
                "mounts": [
                    {"id": 1, "name": "Alliance", "faction": "Alliance"},
                    {"id": 2, "name": "Horde", "faction": "Horde"},
                    {"id": 3, "name": "Neutral", "faction": "Neutral"},
                ]
            },
            factions=("Alliance", "Neutral"),
        )

        self.assertEqual([record["id"] for record in result["owned"]], [1])
        self.assertEqual([record["id"] for record in result["missing"]], [3])

    def test_unknown_faction_value_is_preserved(self):
        records = normalize_mount_catalog({
            "mounts": [{"id": 7, "name": "Mystery", "faction": {"type": "CUSTOM"}}]
        })

        self.assertEqual(records[0]["faction"], "CUSTOM")
        self.assertEqual(records[0]["raw"]["faction"], {"type": "CUSTOM"})
        self.assertEqual(filter_by_faction(records), records)

    def test_absent_values_are_not_invented_and_raw_values_are_retained(self):
        mount = {"mount": {"name": "Unnamed ID"}, "extra": "kept"}
        pet = {"species": {"id": 9}, "quality": 3}

        normalized_mount = normalize_owned_mounts({"mounts": [mount]})[0]
        normalized_pet = normalize_owned_pets({"pets": [pet]})[0]

        self.assertNotIn("id", normalized_mount)
        self.assertNotIn("faction", normalized_mount)
        self.assertEqual(normalized_mount["raw"], mount)
        self.assertNotIn("name", normalized_pet)
        self.assertEqual(normalized_pet["raw"], pet)


if __name__ == "__main__":
    unittest.main()