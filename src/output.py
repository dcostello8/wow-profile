import json
import re
from html import escape
from pathlib import Path

from .config import require_character_field


OUTPUT_DIR = Path("output")
CHARACTER_OUTPUT_DIR = OUTPUT_DIR / "characters"
ROSTER_INDEX_FILE = OUTPUT_DIR / "roster.json"
ROSTER_MARKDOWN_FILE = OUTPUT_DIR / "roster.html"
FULL_ROSTER_MARKDOWN_FILE = OUTPUT_DIR / "fullroster.html"
ACCOUNT_SUMMARY_MARKDOWN_FILE = OUTPUT_DIR / "account_summary.html"
EXPANSION_RELEASE_ORDER = [
    "Midnight",
    "Khaz Algar",
    "Dragon Isles",
    "Shadowlands",
    "Kul Tiran",
    "Zandalari",
    "Legion",
    "Draenor",
    "Pandaria",
    "Cataclysm",
    "Northrend",
    "Outland",
    "Classic",
]
EXPANSION_RELEASE_RANK = {
    expansion.casefold(): index
    for index, expansion in enumerate(EXPANSION_RELEASE_ORDER)
}


def safe_output_stem(character):
    name = require_character_field(character, "name")
    realm_slug = require_character_field(character, "realm_slug")
    character_id = require_character_field(character, "id")
    stem = f"{name}-{realm_slug}-{character_id}".lower()
    return re.sub(r"[^a-z0-9._-]+", "-", stem).strip("-")


def character_output_path(character):
    return CHARACTER_OUTPUT_DIR / f"{safe_output_stem(character)}.json"


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def html_cell(value):
    return escape(str(value if value is not None else ""))


def html_tag(name, value, class_name=None):
    class_attr = f' class="{class_name}"' if class_name else ""
    return f"<{name}{class_attr}>{html_cell(value)}</{name}>"


def table(headers, rows):
    header_html = "".join(html_tag("th", header) for header in headers)
    body_rows = []
    for row in rows:
        body_rows.append(
            "<tr>"
            + "".join(html_tag("td", value) for value in row)
            + "</tr>"
        )
    return (
        '<div class="table-wrap"><table><thead><tr>'
        + header_html
        + "</tr></thead><tbody>"
        + "".join(body_rows)
        + "</tbody></table></div>"
    )


def stat_card(label, value):
    return (
        '<div class="stat">'
        f'<div class="stat-label">{html_cell(label)}</div>'
        f'<div class="stat-value">{html_cell(value)}</div>'
        "</div>"
    )


def local_time(value):
    return (
        f'<time class="local-time" datetime="{html_cell(value)}" data-local-time>'
        f'{html_cell(value)}</time>'
    )


def html_page(title, generated_at, sections):
    body = "\n".join(sections)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html_cell(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #17202a;
      --muted: #637083;
      --line: #d9dee7;
      --accent: #1f6feb;
      --good: #1a7f37;
      --warn: #9a6700;
      --bad: #cf222e;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Segoe UI, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 14px;
      line-height: 1.45;
    }}
    main {{
      width: min(1440px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 48px;
    }}
    header {{
      margin-bottom: 22px;
    }}
    h1 {{
      margin: 0 0 4px;
      font-size: 28px;
      font-weight: 700;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 28px 0 12px;
      font-size: 18px;
      font-weight: 650;
      letter-spacing: 0;
    }}
    .generated {{
      color: var(--muted);
      font-size: 13px;
    }}
    .metadata {{
      color: var(--muted);
      font-size: 12px;
      margin: 6px 0 0;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 10px;
      margin: 16px 0 10px;
    }}
    .stat {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px 14px;
    }}
    .stat-label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    .stat-value {{
      margin-top: 4px;
      font-size: 20px;
      font-weight: 700;
    }}
    .table-wrap {{
      overflow-x: auto;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 760px;
    }}
    th, td {{
      padding: 9px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      white-space: nowrap;
    }}
    th {{
      background: #eef2f7;
      color: #344054;
      font-weight: 650;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    tbody tr:last-child td {{ border-bottom: 0; }}
    .expandable-row {{
      cursor: pointer;
    }}
    .expandable-row:hover td {{
      background: #f8fafc;
    }}
    .toggle-cell {{
      width: 44px;
      text-align: center;
    }}
    .toggle-button {{
      min-height: 26px;
      min-width: 26px;
      padding: 0;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--accent);
      font-weight: 700;
      cursor: pointer;
    }}
    .detail-row[hidden] {{
      display: none;
    }}
    .detail-cell {{
      background: #fbfcfe;
      padding: 14px 16px;
    }}
    .detail-title {{
      margin: 0 0 8px;
      font-weight: 700;
    }}
    .detail-title-spaced {{
      margin-top: 14px;
    }}
    .detail-table {{
      width: auto;
      min-width: 520px;
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 6px;
      overflow: hidden;
    }}
    .detail-empty {{
      color: var(--muted);
    }}
    .muted {{ color: var(--muted); }}
    .status-updated {{ color: var(--good); font-weight: 650; }}
    .status-partial {{ color: var(--warn); font-weight: 650; }}
    .status-failed {{ color: var(--bad); font-weight: 650; }}
    .nav {{
      display: flex;
      gap: 8px;
      margin-top: 14px;
    }}
    .nav a {{
      display: inline-flex;
      align-items: center;
      min-height: 34px;
      padding: 0 12px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
      color: var(--accent);
      text-decoration: none;
      font-weight: 600;
    }}
    .table-tools {{
      display: flex;
      gap: 10px;
      align-items: center;
      margin: 0 0 10px;
    }}
    .table-tools input, .table-tools select {{
      width: min(360px, 100%);
      min-height: 34px;
      padding: 0 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
      color: var(--text);
      font: inherit;
    }}
    th.sortable {{
      cursor: pointer;
      user-select: none;
    }}
    th.sortable button {{
      min-height: 0;
      width: 100%;
      padding: 0;
      border: 0;
      background: transparent;
      color: inherit;
      text-align: left;
      text-transform: inherit;
      letter-spacing: inherit;
      font: inherit;
      cursor: pointer;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{html_cell(title)}</h1>
      <div class="generated">Generated: {html_cell(generated_at)}</div>
      <nav class="nav">
        <a href="/">Account Summary</a>
        <a href="/roster-ui">Roster UI</a>
      </nav>
    </header>
    {body}
  </main>
<script>
  let enabledSortField = "name";
  let enabledSortDirection = "asc";

  function compareText(left, right) {{
    return String(left ?? "").localeCompare(String(right ?? ""), undefined, {{ sensitivity: "base", numeric: true }});
  }}

  function formatLocalTimes() {{
    for (const element of document.querySelectorAll("[data-local-time]")) {{
      const value = element.getAttribute("datetime") || element.textContent;
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) continue;
      element.textContent = new Intl.DateTimeFormat(undefined, {{
        dateStyle: "medium",
        timeStyle: "short",
        timeZoneName: "short"
      }}).format(date);
      element.title = value;
    }}
  }}

  function accountRows() {{
    return Array.from(document.querySelectorAll("#enabled-character-body > tr.expandable-row"));
  }}

  function detailRowFor(row) {{
    return document.getElementById(row.dataset.detailTarget);
  }}

  function updateEnabledSortLabels() {{
    for (const button of document.querySelectorAll("[data-enabled-sort]")) {{
      const label = button.dataset.label || button.textContent.replace(/[ ↑↓]+$/, "");
      button.dataset.label = label;
      button.textContent = label + (button.dataset.enabledSort === enabledSortField ? (enabledSortDirection === "asc" ? " ↑" : " ↓") : "");
    }}
  }}

  function filterEnabledCharacters() {{
    const input = document.getElementById("enabled-character-filter");
    const realmSelect = document.getElementById("enabled-realm-filter");
    const classSelect = document.getElementById("enabled-class-filter");
    const query = input ? input.value.trim().toLowerCase() : "";
    const realm = realmSelect ? realmSelect.value : "";
    const className = classSelect ? classSelect.value : "";
    for (const row of accountRows()) {{
      const detail = detailRowFor(row);
      const matchesQuery = !query || (row.dataset.search || "").includes(query);
      const matchesRealm = !realm || row.dataset.realm === realm;
      const matchesClass = !className || row.dataset.class === className;
      const matches = matchesQuery && matchesRealm && matchesClass;
      row.hidden = !matches;
      if (!matches && detail) detail.hidden = true;
    }}
  }}

  function sortEnabledCharacters(field) {{
    if (enabledSortField === field) {{
      enabledSortDirection = enabledSortDirection === "asc" ? "desc" : "asc";
    }} else {{
      enabledSortField = field;
      enabledSortDirection = "asc";
    }}

    const tbody = document.getElementById("enabled-character-body");
    if (!tbody) return;
    const pairs = accountRows().map(row => [row, detailRowFor(row)]);
    pairs.sort((leftPair, rightPair) => {{
      const left = leftPair[0].dataset[field] || "";
      const right = rightPair[0].dataset[field] || "";
      const result = compareText(left, right) || compareText(leftPair[0].dataset.name, rightPair[0].dataset.name);
      return enabledSortDirection === "asc" ? result : -result;
    }});
    for (const [row, detail] of pairs) {{
      tbody.appendChild(row);
      if (detail) tbody.appendChild(detail);
    }}
    updateEnabledSortLabels();
    filterEnabledCharacters();
  }}

  for (const row of document.querySelectorAll("[data-detail-target]")) {{
    row.addEventListener("click", event => {{
      if (event.target.closest("a")) return;
      const target = document.getElementById(row.dataset.detailTarget);
      if (!target) return;
      const hidden = target.hasAttribute("hidden");
      target.toggleAttribute("hidden", !hidden);
      const button = row.querySelector(".toggle-button");
      if (button) button.textContent = hidden ? "-" : "+";
    }});
  }}
  const enabledFilter = document.getElementById("enabled-character-filter");
  if (enabledFilter) enabledFilter.addEventListener("input", filterEnabledCharacters);
  const enabledRealmFilter = document.getElementById("enabled-realm-filter");
  if (enabledRealmFilter) enabledRealmFilter.addEventListener("change", filterEnabledCharacters);
  const enabledClassFilter = document.getElementById("enabled-class-filter");
  if (enabledClassFilter) enabledClassFilter.addEventListener("change", filterEnabledCharacters);
  for (const button of document.querySelectorAll("[data-enabled-sort]")) {{
    button.addEventListener("click", () => sortEnabledCharacters(button.dataset.enabledSort));
  }}
  formatLocalTimes();
  updateEnabledSortLabels();
</script>
</body>
</html>
"""


def write_roster_markdown(path, index):
    rows = []
    for character in index.get("characters", []):
        sections = character.get("sections") or {}
        updated_sections = sum(
            1
            for result in sections.values()
            if result.get("status") == "updated"
        )
        section_count = len(sections)
        section_text = f"{updated_sections}/{section_count}" if section_count else ""
        rows.append([
            character.get("name") or "",
            character.get("realm") or "",
            character.get("level") or "",
            character.get("character_class") or "",
            character.get("active_spec") or "",
            character.get("local_specs") or "",
            character.get("local_equipment_sets") or "",
            character.get("status") or "",
            section_text,
        ])

    sections = [
        '<section class="stats">'
        + stat_card("Characters", index.get("character_count", len(rows)))
        + stat_card("Updated", index.get("updated_count", 0))
        + stat_card("Partial", index.get("partial_count", 0))
        + stat_card("Failed", index.get("failed_count", 0))
        + "</section>",
        table(
            [
                "Character",
                "Realm",
                "Level",
                "Class",
                "Active Spec",
                "Local Specs/iLvl",
                "Equipment Sets",
                "Status",
                "Sections",
            ],
            rows,
        ),
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        html_page("World of Warcraft Roster", index.get("generated_at"), sections),
        encoding="utf-8",
    )


def markdown_cell(value):
    return str(value if value is not None else "").replace("|", "\\|")


def format_item_level(item_level):
    if not isinstance(item_level, dict):
        return ""
    equipped = item_level.get("equipped")
    average = item_level.get("average")
    if equipped is None and average is None:
        return ""
    if equipped is None:
        return f"avg {average:.1f}" if isinstance(average, float) else f"avg {average}"
    if average is None or average == equipped:
        return f"{equipped:.1f}" if isinstance(equipped, float) else str(equipped)

    equipped_text = f"{equipped:.1f}" if isinstance(equipped, float) else str(equipped)
    average_text = f"{average:.1f}" if isinstance(average, float) else str(average)
    return f"{equipped_text} equipped / {average_text} avg"


def local_spec_rows(document):
    local_data = document.get("local_client_data") or {}
    specs = local_data.get("specs") or {}
    rows = []
    for spec_id, spec in specs.items():
        if not isinstance(spec, dict):
            continue
        rows.append({
            "spec_id": spec.get("spec_id") or spec_id,
            "spec_name": spec.get("spec_name") or "",
            "captured_at": spec.get("captured_at") or "",
            "item_level": spec.get("item_level"),
            "item_level_text": format_item_level(spec.get("item_level")),
        })
    return sorted(
        rows,
        key=lambda row: str(row.get("spec_name") or row.get("spec_id") or ""),
    )


def local_specs_summary(document):
    parts = []
    for row in local_spec_rows(document):
        label = row.get("spec_name") or row.get("spec_id")
        item_level = row.get("item_level_text")
        if label and item_level:
            parts.append(f"{label}: {item_level}")
        elif label:
            parts.append(str(label))
    return "; ".join(parts)


def local_spec_details_html(document):
    rows = local_spec_rows(document)
    if not rows:
        return '<div class="detail-empty">No spec details captured.</div>'

    body = []
    for row in rows:
        body.append(
            "<tr>"
            + html_tag("td", row.get("spec_name"))
            + html_tag("td", row.get("item_level_text"))
            + html_tag("td", row.get("captured_at"))
            + "</tr>"
        )
    return (
        '<table class="detail-table"><thead><tr>'
        + html_tag("th", "Spec")
        + html_tag("th", "Equipped/Character Avg iLvl")
        + html_tag("th", "Captured")
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table>"
    )


def enabled_characters_table(documents):
    sorted_documents = sorted(
        documents,
        key=lambda item: (
            ((item.get("character") or {}).get("realm") or ""),
            ((item.get("character") or {}).get("name") or "").lower(),
        ),
    )
    realms = sorted({
        ((document.get("character") or {}).get("realm") or "")
        for document in sorted_documents
        if (document.get("character") or {}).get("realm")
    })
    classes = sorted({
        (((document.get("sections") or {}).get("profile") or {}).get("character_class") or {}).get("name") or ""
        for document in sorted_documents
        if (((document.get("sections") or {}).get("profile") or {}).get("character_class") or {}).get("name")
    })
    body = []
    for index, document in enumerate(sorted_documents):
        character = document.get("character") or {}
        profile_sections = document.get("sections") or {}
        profile = profile_sections.get("profile") or {}
        professions = ", ".join(primary_profession_names(profile_sections.get("professions")))
        detail_id = f"local-specs-{index}"
        character_name = character.get("name") or ""
        realm_name = character.get("realm") or ""
        class_name = (profile.get("character_class") or {}).get("name") or ""
        active_spec = (profile.get("active_spec") or {}).get("name") or ""
        search_text = " ".join([
            character_name,
            realm_name,
            class_name,
            active_spec,
            professions,
        ]).casefold()
        body.append(
            f'<tr class="expandable-row" data-detail-target="{detail_id}" '
            f'data-name="{html_cell(character_name)}" '
            f'data-realm="{html_cell(realm_name)}" '
            f'data-level="{html_cell(profile.get("level"))}" '
            f'data-class="{html_cell(class_name)}" '
            f'data-spec="{html_cell(active_spec)}" '
            f'data-ilevel="{html_cell(profile.get("equipped_item_level"))}" '
            f'data-search="{html_cell(search_text)}">'
            '<td class="toggle-cell"><button class="toggle-button" type="button">+</button></td>'
            + html_tag("td", character_name)
            + html_tag("td", realm_name)
            + html_tag("td", profile.get("level"))
            + html_tag("td", class_name)
            + html_tag("td", active_spec)
            + html_tag("td", profile.get("equipped_item_level"))
            + html_tag("td", best_mythic_rating(profile_sections.get("mythic_plus")))
            + html_tag("td", professions)
            + "</tr>"
        )
        body.append(
            f'<tr id="{detail_id}" class="detail-row" hidden>'
            '<td class="detail-cell" colspan="9">'
            '<div class="detail-title">Spec Details</div>'
            + local_spec_details_html(document)
            + '<div class="detail-title detail-title-spaced">Equipment Sets</div>'
            + local_equipment_sets_details_html(document)
            + '<div class="detail-title detail-title-spaced">Expansion Skill Levels</div>'
            + profession_skill_details_html(document, f"profession-skills-{index}")
            + "</td></tr>"
        )

    return (
        '<div class="table-tools">'
        '<input id="enabled-character-filter" type="search" placeholder="Filter active characters">'
        '<select id="enabled-realm-filter"><option value="">All realms</option>'
        + "".join(
            f'<option value="{html_cell(realm)}">{html_cell(realm)}</option>'
            for realm in realms
        )
        + "</select>"
        '<select id="enabled-class-filter"><option value="">All classes</option>'
        + "".join(
            f'<option value="{html_cell(class_name)}">{html_cell(class_name)}</option>'
            for class_name in classes
        )
        + "</select>"
        "</div>"
        '<div class="table-wrap"><table><thead><tr>'
        + html_tag("th", "")
        + '<th class="sortable"><button type="button" data-enabled-sort="name">Character</button></th>'
        + '<th class="sortable"><button type="button" data-enabled-sort="realm">Realm</button></th>'
        + '<th class="sortable"><button type="button" data-enabled-sort="level">Level</button></th>'
        + '<th class="sortable"><button type="button" data-enabled-sort="class">Class</button></th>'
        + '<th class="sortable"><button type="button" data-enabled-sort="spec">Active Spec</button></th>'
        + '<th class="sortable"><button type="button" data-enabled-sort="ilevel">iLevel</button></th>'
        + html_tag("th", "Mythic+")
        + html_tag("th", "Professions")
        + '</tr></thead><tbody id="enabled-character-body">'
        + "".join(body)
        + "</tbody></table></div>"
    )


def local_equipment_sets(document):
    local_data = document.get("local_client_data") or {}
    sets = local_data.get("equipment_sets") or []
    return [equipment_set for equipment_set in sets if isinstance(equipment_set, dict)]


def local_equipment_sets_details_html(document):
    rows = []
    for equipment_set in local_equipment_sets(document):
        assigned = equipment_set.get("assigned_spec_name") or ""
        rows.append([
            equipment_set.get("name"),
            assigned,
            format_item_level(equipment_set.get("item_level")),
            "yes" if equipment_set.get("is_equipped") else "no",
        ])

    if not rows:
        return '<div class="detail-empty">No equipment sets captured.</div>'

    return table(["Set", "Assigned Spec", "iLevel", "Equipped"], rows)


def equipment_sets_summary(document):
    parts = []
    for equipment_set in local_equipment_sets(document):
        name = equipment_set.get("name") or equipment_set.get("id")
        if not name:
            continue
        assigned_spec = equipment_set.get("assigned_spec_name")
        if assigned_spec:
            item_level = format_item_level(equipment_set.get("item_level"))
            if item_level:
                parts.append(f"{name}: {item_level} ({assigned_spec})")
            else:
                parts.append(f"{name} ({assigned_spec})")
        else:
            item_level = format_item_level(equipment_set.get("item_level"))
            if item_level:
                parts.append(f"{name}: {item_level}")
            else:
                parts.append(str(name))
    return "; ".join(parts)


def write_full_roster_markdown(path, generated_at, entries):
    grouped = {}
    for entry in entries:
        realm = entry.get("realm") or "Unknown Realm"
        grouped.setdefault(realm, []).append(entry)

    sections = [
        '<section class="stats">'
        + stat_card("Characters", len(entries))
        + stat_card("Realms", len(grouped))
        + "</section>"
    ]

    for realm in sorted(grouped, key=lambda realm_name: (-len(grouped[realm_name]), realm_name)):
        rows = []
        for entry in sorted(grouped[realm], key=lambda item: (item.get("name") or "").lower()):
            rows.append([
                entry.get("name"),
                entry.get("level"),
                entry.get("character_class"),
                entry.get("last_updated"),
            ])
        sections.append(f"<h2>{html_cell(realm)}</h2>")
        sections.append(table(["Character", "Level", "Class", "Last Updated"], rows))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        html_page("Full World of Warcraft Roster", generated_at, sections),
        encoding="utf-8",
    )


def primary_profession_names(professions):
    return [
        profession.get("name")
        for profession in primary_profession_entries(professions)
        if profession.get("name")
    ]


def primary_profession_entries(professions):
    names = []
    for profession in (professions or {}).get("primaries", []):
        if not isinstance(profession, dict):
            continue
        name = (profession.get("profession") or {}).get("name")
        if name:
            names.append({
                "name": name,
                "tiers": profession.get("tiers") or [],
            })
    return names


def profession_tier_rows(profession):
    rows = []
    for tier in profession.get("tiers") or []:
        if not isinstance(tier, dict):
            continue
        tier_name = (tier.get("tier") or {}).get("name")
        skill_points = tier.get("skill_points")
        max_skill_points = tier.get("max_skill_points")
        if not tier_name:
            continue
        if skill_points is not None and max_skill_points is not None:
            skill_text = f"{skill_points}/{max_skill_points}"
        elif skill_points is not None:
            skill_text = str(skill_points)
        else:
            skill_text = ""
        rows.append([tier_name, skill_text])
    return sorted(rows, key=lambda row: profession_tier_sort_key(row[0]))


def profession_tier_sort_key(tier_name):
    normalized = str(tier_name or "").casefold()
    for expansion, rank in EXPANSION_RELEASE_RANK.items():
        if expansion in normalized:
            return (rank, normalized)
    return (len(EXPANSION_RELEASE_ORDER), normalized)


def profession_skill_details_html(document, id_prefix):
    body = []
    professions = primary_profession_entries((document.get("sections") or {}).get("professions"))
    for index, profession in enumerate(professions):
        name = profession.get("name")
        if not name:
            continue
        tier_rows = profession_tier_rows(profession)
        detail_id = f"{id_prefix}-{index}"
        body.append(
            f'<tr class="expandable-row" data-detail-target="{detail_id}">'
            '<td class="toggle-cell"><button class="toggle-button" type="button">+</button></td>'
            + html_tag("td", name)
            + html_tag("td", len(tier_rows))
            + "</tr>"
        )
        body.append(
            f'<tr id="{detail_id}" class="detail-row" hidden>'
            '<td class="detail-cell" colspan="3">'
            + (
                table(["Expansion", "Skill Level"], tier_rows)
                if tier_rows
                else '<div class="detail-empty">No expansion skill levels captured.</div>'
            )
            + "</td></tr>"
        )

    if not body:
        return '<div class="detail-empty">No profession skill levels captured.</div>'

    return (
        '<div class="table-wrap"><table><thead><tr>'
        + html_tag("th", "")
        + html_tag("th", "Profession")
        + html_tag("th", "Expansions")
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def profession_coverage_table(documents):
    realms = {}
    for document in documents:
        character = document.get("character") or {}
        character_name = character.get("name") or ""
        realm = character.get("realm") or "Unknown Realm"
        for profession_name in primary_profession_names((document.get("sections") or {}).get("professions")):
            realm_professions = realms.setdefault(realm, {})
            realm_professions.setdefault(profession_name, []).append(character_name)

    if not realms:
        return '<div class="detail-empty">No professions found.</div>'

    body = []
    for index, realm in enumerate(sorted(realms)):
        detail_id = f"profession-realm-{index}"
        professions = realms[realm]
        body.append(
            f'<tr class="expandable-row" data-detail-target="{detail_id}">'
            '<td class="toggle-cell"><button class="toggle-button" type="button">+</button></td>'
            + html_tag("td", realm)
            + html_tag("td", len(professions))
            + "</tr>"
        )

        rows = []
        for profession_name in sorted(professions):
            characters = sorted(name for name in professions[profession_name] if name)
            rows.append([profession_name, ", ".join(characters)])
        body.append(
            f'<tr id="{detail_id}" class="detail-row" hidden>'
            '<td class="detail-cell" colspan="3">'
            + table(["Profession", "Characters"], rows)
            + "</td></tr>"
        )

    return (
        '<div class="table-wrap"><table><thead><tr>'
        + html_tag("th", "")
        + html_tag("th", "Realm")
        + html_tag("th", "Professions")
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def best_mythic_rating(mythic_plus):
    if not mythic_plus:
        return ""
    rating = mythic_plus.get("current_mythic_rating") or mythic_plus.get("mythic_rating")
    if isinstance(rating, dict):
        return rating.get("rating") or ""
    return rating or ""


def active_character_documents(roster_characters, character_documents):
    active_keys = {
        character_identity_key(character)
        for character in roster_characters
        if character.get("enabled") is True
    }
    return [
        document
        for document in character_documents
        if character_identity_key(document.get("character") or {}) in active_keys
    ]


def character_identity_key(character):
    if character.get("key"):
        return str(character.get("key"))
    region = character.get("region")
    character_id = character.get("id")
    if region and character_id is not None:
        return f"{region}:id:{character_id}"
    return "|".join([
        str(region or ""),
        str(character.get("realm_slug") or character.get("realm") or "").casefold(),
        str(character.get("name") or "").casefold(),
    ])


def write_account_summary_markdown(path, generated_at, roster, index, character_documents):
    roster_characters = [
        character
        for character in roster.get("characters", [])
        if isinstance(character, dict)
    ]
    active_documents = active_character_documents(roster_characters, character_documents)
    enabled_count = sum(1 for character in roster_characters if character.get("enabled"))
    stale_count = sum(1 for character in roster_characters if character.get("stale"))
    realms = sorted({
        character.get("realm") or "Unknown Realm"
        for character in roster_characters
    })

    sections = [
        '<section class="stats">'
        + stat_card("Characters Discovered", len(roster_characters))
        + stat_card("Active", enabled_count)
        + stat_card("Realms", len(realms))
        + stat_card("Stale Entries", stale_count)
        + stat_card("Detailed Profiles", len(active_documents))
        + "</section>"
    ]

    if index:
        sections.append(
            '<section class="stats">'
            + stat_card("Updated", index.get("updated_count", 0))
            + stat_card("Partial", index.get("partial_count", 0))
            + stat_card("Failed", index.get("failed_count", 0))
            + "</section>"
        )
        if index.get("generated_at"):
            sections.append(
                '<div class="metadata">Last Update: '
                + local_time(index.get("generated_at"))
                + "</div>"
            )

    sections.append("<h2>Active Characters</h2>")
    sections.append(enabled_characters_table(active_documents))

    class_counts = {}
    for document in active_documents:
        profile_sections = document.get("sections") or {}
        profile = profile_sections.get("profile") or {}
        class_name = (profile.get("character_class") or {}).get("name")
        if class_name:
            class_counts[class_name] = class_counts.get(class_name, 0) + 1

    sections.append("<h2>Active Class Coverage</h2>")
    sections.append(table(
        ["Class", "Characters"],
        [[class_name, class_counts[class_name]] for class_name in sorted(class_counts)],
    ))

    sections.append("<h2>Active Profession Coverage</h2>")
    sections.append(profession_coverage_table(active_documents))

    grouped = {}
    for character in roster_characters:
        realm = character.get("realm") or "Unknown Realm"
        grouped.setdefault(realm, []).append(character)
    sections.append("<h2>Roster By Realm</h2>")
    for realm in sorted(grouped):
        rows = []
        for character in sorted(grouped[realm], key=lambda item: (item.get("name") or "").lower()):
            rows.append([
                character.get("name"),
                "yes" if character.get("enabled") else "no",
                "yes" if character.get("stale") else "no",
            ])
        sections.append(f"<h2>{html_cell(realm)}</h2>")
        sections.append(table(["Character", "Active", "Stale"], rows))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        html_page("Account Summary", generated_at, sections),
        encoding="utf-8",
    )


def summarize_profile(profile):
    if not profile:
        return {}
    return {
        "level": profile.get("level"),
        "faction": (profile.get("faction") or {}).get("name"),
        "race": (profile.get("race") or {}).get("name"),
        "character_class": (profile.get("character_class") or {}).get("name"),
        "active_spec": (profile.get("active_spec") or {}).get("name"),
        "guild": (profile.get("guild") or {}).get("name"),
        "last_login_timestamp": profile.get("last_login_timestamp"),
    }


def roster_index_entry(character, status, profile_path=None, profile=None, error=None):
    entry = {
        "key": character.get("key"),
        "name": character.get("name"),
        "realm": character.get("realm"),
        "realm_slug": character.get("realm_slug"),
        "region": character.get("region"),
        "id": character.get("id"),
        "enabled": bool(character.get("enabled")),
        "stale": bool(character.get("stale", False)),
        "status": status,
    }
    if profile_path:
        entry["profile_path"] = str(profile_path).replace("\\", "/")
    entry.update(summarize_profile(profile))
    if error:
        entry["error"] = error
    return entry
