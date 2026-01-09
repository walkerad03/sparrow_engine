
from sparrow.core.registry import ComponentRegistry


# Define local test components to ensure isolation
class CompA:
    pass


class CompB:
    pass


class CompC:
    pass


def test_registry_assigns_unique_ids():
    """Ensure different types get different integer IDs."""
    id_a = ComponentRegistry.get_id(CompA)
    id_b = ComponentRegistry.get_id(CompB)

    assert isinstance(id_a, int)
    assert isinstance(id_b, int)
    assert id_a != id_b


def test_registry_assigns_powers_of_two():
    """Ensure masks are 1, 2, 4, 8, etc."""
    mask_a = ComponentRegistry.get_mask(CompA)
    mask_b = ComponentRegistry.get_mask(CompB)

    # Check if they are powers of two
    # (n & (n-1) == 0) is a binary trick to check for power of 2
    assert (mask_a & (mask_a - 1)) == 0
    assert (mask_b & (mask_b - 1)) == 0

    # Ensure they are distinct bits
    assert (mask_a & mask_b) == 0


def test_mask_composition():
    """Verify that OR-ing masks combines them correctly."""
    mask_a = ComponentRegistry.get_mask(CompA)
    mask_b = ComponentRegistry.get_mask(CompB)

    combined = mask_a | mask_b

    # The combined mask should 'contain' both individual masks
    assert (combined & mask_a) == mask_a
    assert (combined & mask_b) == mask_b

    # It should NOT contain a mask for a component we didn't add
    mask_c = ComponentRegistry.get_mask(CompC)
    assert (combined & mask_c) == 0


def test_registry_determinism():
    """Ensure asking for the same component twice yields the same ID."""
    id_1 = ComponentRegistry.get_id(CompA)
    id_2 = ComponentRegistry.get_id(CompA)

    assert id_1 == id_2
