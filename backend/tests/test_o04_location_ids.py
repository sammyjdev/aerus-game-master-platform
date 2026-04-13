import pytest


def test_location_ids_are_english():
    """All location IDs in travel.yaml should be English snake_case."""
    import yaml
    with open("config/travel.yaml") as f:
        data = yaml.safe_load(f)
    portuguese_patterns = ["fendas_de", "passagem_", "coracao_", "urbes_ambulantes"]
    for loc_id in data.get("locations", {}).keys():
        for pattern in portuguese_patterns:
            assert pattern not in loc_id, (
                f"Location ID '{loc_id}' appears to be non-English (pattern: '{pattern}')"
            )


def test_route_ids_use_normalized_locations():
    """Route destination IDs should match location keys."""
    import yaml
    with open("config/travel.yaml") as f:
        data = yaml.safe_load(f)
    location_ids = set(data.get("locations", {}).keys())
    for route_id, route in data.get("routes", {}).items():
        for segment in route.get("segments", []):
            dest = segment.get("destination")
            if dest:
                assert dest in location_ids, (
                    f"Route '{route_id}' references unknown location '{dest}'"
                )


def test_renamed_location_ids_exist():
    """The four renamed English IDs should exist as location keys."""
    import yaml
    with open("config/travel.yaml") as f:
        data = yaml.safe_load(f)
    location_ids = set(data.get("locations", {}).keys())
    expected = {"gorath_fissures", "ondrek_passage", "ash_heart", "wandering_cities"}
    for loc_id in expected:
        assert loc_id in location_ids, f"Expected location '{loc_id}' not found in travel.yaml"


def test_old_portuguese_ids_absent():
    """Old Portuguese IDs must not appear anywhere in travel.yaml."""
    with open("config/travel.yaml") as f:
        content = f.read()
    old_ids = ["fendas_de_gorath", "passagem_ondrek", "coracao_cinzas", "urbes_ambulantes"]
    for old_id in old_ids:
        assert old_id not in content, (
            f"Old Portuguese ID '{old_id}' still present in travel.yaml"
        )


def test_route_keys_reference_valid_locations():
    """All location IDs embedded in route keys should exist in locations."""
    import yaml
    with open("config/travel.yaml") as f:
        data = yaml.safe_load(f)
    location_ids = set(data.get("locations", {}).keys())
    for route_id in data.get("routes", {}).keys():
        parts = route_id.split("->")
        if len(parts) == 2:
            src, dst = parts
            assert src in location_ids, (
                f"Route '{route_id}' has unknown source location '{src}'"
            )
            assert dst in location_ids, (
                f"Route '{route_id}' has unknown destination location '{dst}'"
            )
