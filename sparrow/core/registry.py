from typing import Any, Dict, Type

from sparrow.types import ArchetypeMask


class ComponentRegistry:
    _counter: int = 0
    _type_to_id: Dict[Type[Any], int] = {}
    _type_to_mask: Dict[Type[Any], ArchetypeMask] = {}

    @classmethod
    def get_id(cls, component_type: Type[Any]) -> int:
        if component_type not in cls._type_to_id:
            cls._type_to_id[component_type] = cls._counter
            cls._counter += 1
        return cls._type_to_id[component_type]

    @classmethod
    def get_mask(cls, component_type: Type[Any]) -> ArchetypeMask:
        if component_type not in cls._type_to_mask:
            # Calculate 1 << id
            bit = 1 << cls.get_id(component_type)
            cls._type_to_mask[component_type] = ArchetypeMask(bit)
        return cls._type_to_mask[component_type]
