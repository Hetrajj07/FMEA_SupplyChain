import concurrent.futures

import pytest

from mitigation_module import dynamic_network as dn


@pytest.fixture(autouse=True)
def _clean_dynamic_routes():
    dn.reset_dynamic_routes()
    yield
    dn.reset_dynamic_routes()


def test_concurrent_same_city_creates_routes_once(monkeypatch):
    monkeypatch.setattr(dn, "get_warehouse_list", lambda: ["W1", "W2", "W3"])
    monkeypatch.setattr(dn, "get_hub_list", lambda: ["H1", "H2"])

    city = "RaceCity"
    expected_total = 3 + (3 * 2)

    def _call():
        return tuple(dn.get_routes_for_city(city, include_multihop=True))

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: _call(), range(64)))

    # All callers should observe the same stable route set.
    unique_results = {r for r in results}
    assert len(unique_results) == 1
    only = list(unique_results)[0]
    assert len(only) == expected_total
    assert len(set(only)) == expected_total

    # Repeated non-concurrent call must not append duplicate routes.
    again = dn.get_routes_for_city(city, include_multihop=True)
    assert len(again) == expected_total
    assert set(again) == set(only)


def test_concurrent_multi_city_has_unique_route_ids(monkeypatch):
    monkeypatch.setattr(dn, "get_warehouse_list", lambda: ["W1", "W2"])
    monkeypatch.setattr(dn, "get_hub_list", lambda: ["H1", "H2", "H3"])

    cities = ["A", "B", "C", "D", "E"]
    expected_per_city = 2 + (2 * 3)

    def _call(city):
        return city, dn.get_routes_for_city(city, include_multihop=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(cities)) as pool:
        output = list(pool.map(_call, cities))

    all_ids = []
    for city, route_ids in output:
        assert len(route_ids) == expected_per_city, f"unexpected route count for {city}"
        assert len(route_ids) == len(set(route_ids)), f"duplicate IDs within {city}"
        all_ids.extend(route_ids)

    assert len(all_ids) == len(set(all_ids)), "route IDs collided across cities"
