import pytest

from tests.conftest import Position


def test_mutate_existing_component(world):
    e = world.create_entity(Position(10, 10))

    # Valid mutation
    world.mutate_component(e, Position(20, 20))
    assert world.component(e, Position).x == 20


def test_mutate_missing_component_raises_error(world):
    e = world.create_entity()  # No components

    # Should fail because entity doesn't have Position yet
    with pytest.raises(KeyError) as exc:
        world.mutate_component(e, Position(10, 10))

    assert "Component missing" in str(exc.value)


def test_mutate_missing_entity(world):
    with pytest.raises(KeyError):
        world.mutate_component(99999, Position(1, 1))
