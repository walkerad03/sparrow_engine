
from tests.conftest import Health, Position, Velocity


def test_create_entity(world):
    e1 = world.create_entity()
    e2 = world.create_entity()
    assert e1 != e2
    assert isinstance(e1, int)


def test_add_component_moves_archetype(world):
    """Verifies that adding a component migrates the entity correctly."""
    e = world.create_entity()

    # Initial state: Empty Archetype
    assert not world.has(e, Position)

    # Add Position -> Moves to [Position] Archetype
    world.add_component(e, Position(10, 20))
    pos = world.component(e, Position)
    assert pos.x == 10
    assert world.has(e, Position)

    # Add Velocity -> Moves to [Position, Velocity] Archetype
    world.add_component(e, Velocity(1, 1))
    assert world.has(e, Velocity)
    # Ensure Position data wasn't lost during move
    assert world.component(e, Position).x == 10


def test_remove_component(world):
    e = world.create_entity(Position(0, 0), Velocity(1, 1))

    assert world.has(e, Position)
    world.remove_component(e, Position)

    assert not world.has(e, Position)
    assert world.has(e, Velocity)  # Should still be there


def test_query_join(world):
    """The most critical test: Does the query filter correctly?"""
    # Entity A: Pos + Vel
    e1 = world.create_entity(Position(0, 0), Velocity(0, 0))
    # Entity B: Pos Only
    e2 = world.create_entity(Position(1, 1))
    # Entity C: Vel Only
    e3 = world.create_entity(Velocity(2, 2))
    # Entity D: Pos + Vel + Health
    e4 = world.create_entity(Position(3, 3), Velocity(3, 3), Health(100))

    # Query: Join(Position, Velocity)
    # Should match e1 and e4. Should NOT match e2 (missing vel) or e3 (missing pos).
    results = list(world.join(Position, Velocity))

    # Check IDs
    found_ids = {r[0] for r in results}
    assert found_ids == {e1, e4}

    # Check Data Unpacking
    for eid, pos, vel in results:
        assert isinstance(pos, Position)
        assert isinstance(vel, Velocity)
