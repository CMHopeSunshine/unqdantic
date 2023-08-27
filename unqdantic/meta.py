from typing import Any, Optional, Type

from .core import Database


class MetaConfig:
    name: str
    db: Optional[Database] = None
    by_alias: bool = False


def mix_meta_config(
    self_config: Optional[Type[MetaConfig]],
    parent_config: Type[MetaConfig],
    **namespace: Any,
) -> Type[MetaConfig]:
    if not self_config:
        base_classes = (parent_config,)
    elif self_config == parent_config:
        base_classes = (self_config,)
    else:
        base_classes = self_config, parent_config

    return type("Meta", base_classes, namespace)
