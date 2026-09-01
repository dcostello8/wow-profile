import unittest

from src.output import (
    enabled_characters_table,
    equipment_sets_summary,
    format_item_level,
    local_specs_summary,
    profession_coverage_table,
    write_account_summary_markdown,
)


class OutputTests(unittest.TestCase):
    def test_format_item_level_equipped_and_average(self):
        self.assertEqual(
            format_item_level({"equipped": 681.25, "average": 684.375}),
            "681.2 equipped / 684.4 avg",
        )

    def test_local_specs_summary(self):
        document = {
            "local_client_data": {
                "specs": {
                    "262": {
                        "spec_id": 262,
                        "spec_name": "Elemental",
                        "item_level": {"equipped": 681.25, "average": 684.375},
                    },
                    "264": {
                        "spec_id": 264,
                        "spec_name": "Restoration",
                        "item_level": {"equipped": 680.75, "average": 682.5},
                    },
                }
            }
        }

        self.assertEqual(
            local_specs_summary(document),
            "Elemental: 681.2 equipped / 684.4 avg; Restoration: 680.8 equipped / 682.5 avg",
        )

    def test_equipment_sets_summary_includes_ilevel_and_optional_spec(self):
        document = {
            "local_client_data": {
                "equipment_sets": [
                    {
                        "name": "Resto",
                        "assigned_spec_name": "Restoration",
                        "item_level": {"equipped": 680.5},
                    },
                    {
                        "name": "Fishing",
                        "item_level": {"equipped": 645},
                    },
                ]
            }
        }

        self.assertEqual(
            equipment_sets_summary(document),
            "Resto: 680.5 (Restoration); Fishing: 645",
        )

    def test_enabled_characters_table_contains_expandable_spec_details(self):
        document = {
            "character": {"name": "Thaigan", "realm": "Windrunner"},
            "sections": {
                "profile": {
                    "level": 90,
                    "character_class": {"name": "Shaman"},
                    "active_spec": {"name": "Restoration"},
                    "equipped_item_level": 282,
                }
            },
            "local_client_data": {
                "specs": {
                    "264": {
                        "spec_id": 264,
                        "spec_name": "Restoration",
                        "captured_at": "2026-08-31T20:57:23Z",
                        "item_level": {"equipped": 282.4, "average": 286.8},
                    }
                },
                "equipment_sets": [
                    {
                        "id": 1,
                        "name": "Resto",
                        "assigned_spec_name": "Restoration",
                        "assigned_spec_id": 264,
                        "is_equipped": True,
                        "num_equipped": 15,
                        "num_items": 15,
                        "item_level": {"equipped": 282.4},
                    }
                ],
            },
        }
        document["sections"]["professions"] = {
            "primaries": [
                {
                    "profession": {"name": "Herbalism"},
                    "tiers": [
                        {
                            "tier": {"name": "Classic Herbalism"},
                            "skill_points": 300,
                            "max_skill_points": 300,
                        },
                        {
                            "tier": {"name": "Khaz Algar Herbalism"},
                            "skill_points": 88,
                            "max_skill_points": 100,
                        },
                        {
                            "tier": {"name": "Midnight Herbalism"},
                            "skill_points": 12,
                            "max_skill_points": 100,
                        }
                    ],
                }
            ]
        }

        html = enabled_characters_table([document])

        self.assertIn('data-detail-target="local-specs-0"', html)
        self.assertIn("Spec Details", html)
        self.assertIn("Equipment Sets", html)
        self.assertNotIn("Local Equipment Sets", html)
        self.assertNotIn("<th>Spec ID</th>", html)
        self.assertIn('id="enabled-character-filter"', html)
        self.assertIn('id="enabled-realm-filter"', html)
        self.assertIn('id="enabled-class-filter"', html)
        self.assertIn('<option value="Windrunner">Windrunner</option>', html)
        self.assertIn('<option value="Shaman">Shaman</option>', html)
        self.assertIn('data-enabled-sort="name"', html)
        self.assertIn('data-enabled-sort="realm"', html)
        self.assertIn("Restoration", html)
        self.assertIn("282.4 equipped / 286.8 avg", html)
        self.assertIn("Resto", html)
        self.assertIn("Expansion Skill Levels", html)
        self.assertIn("Herbalism", html)
        self.assertIn('data-detail-target="profession-skills-0-0"', html)
        self.assertIn("<th>Expansion</th>", html)
        self.assertIn("<th>Skill Level</th>", html)
        self.assertIn("Khaz Algar Herbalism", html)
        self.assertLess(html.index("Midnight Herbalism"), html.index("Khaz Algar Herbalism"))
        self.assertLess(html.index("Khaz Algar Herbalism"), html.index("Classic Herbalism"))
        self.assertIn("88/100", html)
        self.assertNotIn("Khaz Algar Herbalism: 88/100", html)
        self.assertNotIn("Set ID", html)
        self.assertNotIn("Restoration (264)", html)
        self.assertNotIn("Items Equipped", html)
        self.assertNotIn("15/15", html)

    def test_profession_coverage_rolls_up_by_realm(self):
        documents = [
            {
                "character": {"name": "Thaigan", "realm": "Windrunner"},
                "sections": {
                    "professions": {
                        "primaries": [
                            {
                                "profession": {"name": "Herbalism"},
                                "tiers": [
                                    {
                                        "tier": {"name": "Khaz Algar Herbalism"},
                                        "skill_points": 88,
                                        "max_skill_points": 100,
                                    }
                                ],
                            },
                            {"profession": {"name": "Skinning"}},
                        ]
                    }
                },
            },
            {
                "character": {"name": "Jaedon", "realm": "Windrunner"},
                "sections": {
                    "professions": {
                        "primaries": [
                            {
                                "profession": {"name": "Mining"},
                                "tiers": [
                                    {
                                        "tier": {"name": "Midnight Mining"},
                                        "skill_points": 12,
                                        "max_skill_points": 100,
                                    }
                                ],
                            },
                        ]
                    }
                },
            },
            {
                "character": {"name": "Another", "realm": "Moon Guard"},
                "sections": {
                    "professions": {
                        "primaries": [
                            {"profession": {"name": "Herbalism"}},
                        ]
                    }
                },
            },
        ]

        html = profession_coverage_table(documents)

        self.assertIn('data-detail-target="profession-realm-0"', html)
        self.assertIn("Windrunner", html)
        self.assertIn("Moon Guard", html)
        self.assertIn("<th>Profession</th>", html)
        self.assertIn("<th>Characters</th>", html)
        self.assertNotIn("<th>Expansion Skill Levels</th>", html)
        self.assertIn("Herbalism", html)
        self.assertIn("Skinning", html)
        self.assertIn("Mining", html)
        self.assertIn("Thaigan", html)
        self.assertIn("Jaedon", html)
        self.assertNotIn("Khaz Algar Herbalism: 88/100", html)
        self.assertNotIn("Midnight Mining: 12/100", html)

    def test_account_summary_last_update_is_quiet_local_time(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "account_summary.html"
            write_account_summary_markdown(
                path,
                "2026-09-01T19:00:00+00:00",
                {"characters": []},
                {
                    "generated_at": "2026-09-01T18:30:00+00:00",
                    "updated_count": 2,
                    "partial_count": 1,
                    "failed_count": 0,
                },
                [],
            )
            html = path.read_text(encoding="utf-8")

        self.assertIn('<div class="metadata">Last Update: ', html)
        self.assertIn('datetime="2026-09-01T18:30:00+00:00" data-local-time', html)
        self.assertIn("formatLocalTimes()", html)
        self.assertIn("#enabled-character-body > tr.expandable-row", html)
        self.assertIn("<h2>Active Characters</h2>", html)
        self.assertIn('<div class="stat-label">Active</div>', html)
        self.assertIn("<h2>Active Class Coverage</h2>", html)
        self.assertIn("<h2>Active Profession Coverage</h2>", html)
        self.assertNotIn('<div class="stat-label">Last Update</div>', html)
        self.assertNotIn("<h2>Enabled Characters</h2>", html)
        self.assertNotIn("<h2>Class Coverage</h2>", html)
        self.assertNotIn("<h2>Profession Coverage</h2>", html)


if __name__ == "__main__":
    unittest.main()
