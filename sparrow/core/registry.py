from dataclasses import fields, is_dataclass
from typing import Any, Dict, Type

from sparrow.types import ArchetypeMask, EntityId, Quaternion, Vector2, Vector3


class ComponentRegistry:
    _counter: int = 0
    _type_to_id: Dict[Type[Any], int] = {}
    _type_to_mask: Dict[Type[Any], ArchetypeMask] = {}

    @classmethod
    def get_soa_dtype(cls, comp_type: Type[Any]) -> Any:
        """Generate a NumPy dtype for a dataclass automatically."""
        if not is_dataclass(comp_type):
            return None

        TYPE_MAP = {
            float: ("f4", ()),
            int: ("i4", ()),
            bool: ("?", ()),
            Vector2: ("f4", (2,)),
            Vector3: ("f4", (3,)),
            Quaternion: ("f4", (4,)),
            EntityId: ("i8", ()),
        }

        dtype_fields = []
        for field in fields(comp_type):
            t = field.type
            if t in TYPE_MAP:
                dt, shape = TYPE_MAP[t]
                if shape:
                    dtype_fields.append((field.name, dt, shape))
                else:
                    dtype_fields.append((field.name, dt))

        return dtype_fields if dtype_fields else None

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
