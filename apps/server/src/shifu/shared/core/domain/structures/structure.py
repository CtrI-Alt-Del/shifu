from dataclasses import dataclass
from typing import dataclass_transform


@dataclass_transform(frozen_default=True, kw_only_default=True)
def structure[StructureType](cls: type[StructureType]) -> type[StructureType]:
    return dataclass(cls, frozen=True, kw_only=True, slots=True)
