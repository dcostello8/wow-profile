import unittest

from src.output import (
    active_character_documents,
    enabled_characters_table,
    equipment_sets_summary,
    format_item_level,
    local_specs_summary,
    profession_coverage_table,
    write_account_summary_markdown,
)


class OutputTests(unittest.TestCase):
    def test_active_character_documents_filters_inactive_roster_entries(self):
        roster_characters = [
            {
                "key": "us:id:1",
                "name": "Activeone",
                "realm": "Windrunner",
                "enabled": True,
            },
            {
                "key": "us:id:2",
                "name": "Inactiveone",
                "realm": "Darrowmere",
                "enabled": False,
            },
        ]
        documents = [
            {"character": {"key": "us:id:1", "name": "Activeone"}},
            {"character": {"key": "us:id:2", "name": "Inactiveone"}},
        ]

        active = active_character_documents(roster_characters, documents)

        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["character"]["name"], "Activeone")

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
                    "faction": {"name": "Alliance"},
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
        self.assertIn('id="enabled-faction-filter"', html)
        self.assertIn('id="enabled-class-filter"', html)
        self.assertIn('<option value="Windrunner">Windrunner</option>', html)
        self.assertIn('<option value="Alliance">Alliance</option>', html)
        self.assertIn('data-faction="Alliance"', html)
        self.assertIn(">Faction</button></th>", html)
        self.assertIn('<option value="Shaman">Shaman</option>', html)
        self.assertIn('data-enabled-sort="name"', html)
        self.assertIn('data-enabled-sort="realm"', html)
        self.assertIn('data-enabled-sort="faction"', html)
        self.assertIn('data-character-refresh=', html)
        self.assertIn('data-equipment-target="equipment-sets-0"', html)
        self.assertIn('>Equipment Sets</button>', html)
        self.assertIn("Restoration", html)
        self.assertIn("282.4 equipped / 286.8 avg", html)
        self.assertIn('datetime="2026-08-31T20:57:23Z" data-local-time', html)
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
        self.assertIn('String(value).padStart(2, "0")', html)
        self.assertIn("hours % 12 || 12", html)
        self.assertIn('hours < 12 ? "AM" : "PM"', html)
        self.assertIn('timeZoneName: "short"', html)
        self.assertIn("formatToParts(date)", html)
        self.assertNotIn('dateStyle: "medium"', html)
        self.assertNotIn('timeStyle: "short"', html)
        self.assertIn("#enabled-character-body > tr.expandable-row", html)
        self.assertIn("<h2>Active Characters</h2>", html)
        self.assertIn('data-summary-command="update"', html)
        self.assertIn('data-summary-command="discover"', html)
        self.assertIn('id="equipment-modal-backdrop"', html)
        self.assertIn('id="equipment-modal-body"', html)
        self.assertIn('openEquipmentModal', html)
        self.assertIn("width: 180px", html)
        self.assertIn("display: grid", html)
        self.assertIn("viewport-positioned", html)
        self.assertIn("positionRowMenu", html)
        self.assertIn("function closeRowMenus()", html)
        self.assertIn('if (!event.target.closest(".row-menu")) closeRowMenus();', html)
        self.assertIn(".equipment-modal .table-wrap", html)
        self.assertIn("overflow-x: hidden", html)
        self.assertIn("table-layout: fixed", html)
        self.assertIn("otherMenu.open = false", html)
        self.assertIn('"/api/update/status"', html)
        self.assertIn('"/api/discover/status"', html)
        self.assertIn('"/api/summary/refresh"', html)
        self.assertIn("Refreshing Account Summary...", html)
        self.assertIn('split("\\\\n").slice(-20).join("\\\\n")', html)
        self.assertIn("reloadAccountSummary", html)
        self.assertIn("Open Account Summary through http://127.0.0.1:8765/", html)
        self.assertNotIn('<nav class="nav">', html)
        self.assertNotIn('<a href="/">Account Summary</a>', html)
        self.assertNotIn('<a href="/roster-ui">Roster UI</a>', html)
        self.assertIn('<div class="stat-label">Characters Discovered</div>', html)
        self.assertIn('<div class="stat-label">Active</div>', html)
        self.assertIn('<div class="stat-label">Realms</div>', html)
        self.assertNotIn('<div class="stat-label">Stale Entries</div>', html)
        self.assertNotIn('<div class="stat-label">Detailed Profiles</div>', html)
        self.assertNotIn('<div class="stat-label">Updated</div>', html)
        self.assertNotIn('<div class="stat-label">Partial</div>', html)
        self.assertNotIn('<div class="stat-label">Failed</div>', html)
        self.assertNotIn('<div class="stat-label">Set Inactive</div>', html)
        self.assertIn("<h2>Active Class Coverage</h2>", html)
        self.assertIn("<h2>Active Profession Coverage</h2>", html)
        self.assertNotIn('<div class="stat-label">Last Update</div>', html)
        self.assertNotIn("<h2>Enabled Characters</h2>", html)
        self.assertNotIn("<h2>Class Coverage</h2>", html)
        self.assertNotIn("<h2>Profession Coverage</h2>", html)

    def test_account_summary_lists_recent_inactive_changes(self):
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
                    "updated_count": 0,
                    "partial_count": 0,
                    "failed_count": 1,
                    "deactivated_count": 1,
                    "deactivated_characters": [
                        {
                            "name": "Absecon",
                            "realm": "Darrowmere",
                            "status_code": 404,
                            "reason": "public profile unavailable",
                        }
                    ],
                },
                [],
            )
            html = path.read_text(encoding="utf-8")

        self.assertIn("<h2>Recent Inactive Changes</h2>", html)
        self.assertIn("Absecon", html)
        self.assertIn("Darrowmere", html)
        self.assertIn("404", html)
        self.assertIn("public profile unavailable", html)

    def test_account_summary_active_sections_exclude_inactive_documents(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "account_summary.html"
            write_account_summary_markdown(
                path,
                "2026-09-01T19:00:00+00:00",
                {
                    "characters": [
                        {
                            "key": "us:id:1",
                            "name": "Activeone",
                            "realm": "Windrunner",
                            "enabled": True,
                        },
                        {
                            "key": "us:id:2",
                            "name": "Absecon",
                            "realm": "Darrowmere",
                            "enabled": False,
                        },
                    ]
                },
                {},
                [
                    {
                        "character": {"key": "us:id:1", "name": "Activeone", "realm": "Windrunner"},
                        "sections": {"profile": {"faction": {"name": "Alliance"}, "character_class": {"name": "Mage"}}},
                    },
                    {
                        "character": {"key": "us:id:2", "name": "Absecon", "realm": "Darrowmere"},
                        "sections": {"profile": {"faction": {"name": "Horde"}, "character_class": {"name": "Warrior"}}},
                    },
                ],
            )
            html = path.read_text(encoding="utf-8")

        active_section = html.split("<h2>Active Characters</h2>", 1)[1].split("<h2>Active Class Coverage</h2>", 1)[0]
        class_section = html.split("<h2>Active Class Coverage</h2>", 1)[1].split("<h2>Active Profession Coverage</h2>", 1)[0]

        self.assertIn("Activeone", active_section)
        self.assertNotIn("Absecon", active_section)
        self.assertIn("Alliance", active_section)
        self.assertNotIn("Horde", active_section)
        self.assertIn("Mage", class_section)
        self.assertNotIn("Warrior", class_section)

    def test_account_summary_roster_by_realm_renders_active_switches(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "account_summary.html"
            write_account_summary_markdown(
                path,
                "2026-09-01T19:00:00+00:00",
                {
                    "characters": [
                        {
                            "key": "us:id:1",
                            "name": "Activeone",
                            "realm": "Windrunner",
                            "enabled": True,
                        },
                        {
                            "key": "us:id:2",
                            "name": "Inactiveone",
                            "realm": "Windrunner",
                            "enabled": False,
                        },
                        {
                            "key": "us:id:3",
                            "name": "Staleone",
                            "realm": "Oldrealm",
                            "enabled": True,
                            "stale": True,
                        },
                    ]
                },
                {},
                [
                    {
                        "character": {"key": "us:id:3", "name": "Staleone", "realm": "Oldrealm"},
                        "sections": {"profile": {"character_class": {"name": "Mage"}}},
                    }
                ],
            )
            html = path.read_text(encoding="utf-8")

        roster_section = html.split("<h2>Roster By Realm</h2>", 1)[1]
        active_section = html.split("<h2>Active Characters</h2>", 1)[1].split("<h2>Active Class Coverage</h2>", 1)[0]

        self.assertIn('data-summary-command="update"', active_section)
        self.assertIn('data-summary-command="discover"', roster_section)
        self.assertIn('data-detail-target="roster-realm-0"', roster_section)
        self.assertIn('<tr id="roster-realm-0" class="detail-row" hidden>', roster_section)
        self.assertIn('<div class="stat-label">Characters Discovered</div><div class="stat-value">2</div>', html)
        self.assertIn('<div class="stat-label">Realms</div><div class="stat-value">1</div>', html)
        self.assertIn("<th>Realm</th>", roster_section)
        self.assertNotIn("<th>Stale</th>", roster_section)
        self.assertIn("<td>Windrunner</td>", roster_section)
        self.assertNotIn("Oldrealm", roster_section)
        self.assertNotIn("Staleone", roster_section)
        self.assertNotIn("Staleone", active_section)
        self.assertIn('class="active-switch"', roster_section)
        self.assertIn('data-roster-active-id="us:id:1"', roster_section)
        self.assertIn('data-character-name="Activeone" checked', roster_section)
        self.assertIn('data-roster-active-id="us:id:2"', roster_section)
        self.assertNotIn("<h2>Windrunner</h2>", roster_section)
        self.assertIn('"/api/characters/enabled"', html)
        self.assertIn('"/api/characters/activate"', html)
        self.assertIn('id="account-status-modal-backdrop"', html)
        self.assertIn("Activating Character", html)
        self.assertIn("window.location.reload()", html)


if __name__ == "__main__":
    unittest.main()
