from functools import reduce
from typing import Any, Dict, List


def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]):
    result = {}
    for key in set(a.keys()).union(b.keys()):
        if (
            key in a
            and key in b
            and isinstance(a[key], dict)
            and isinstance(b[key], dict)
        ):
            result[key] = merge_dicts(a[key], b[key])
        elif key in a:
            result[key] = b[key] if key in b else a[key]
        else:
            result[key] = b[key]
    return result


def generate_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    result = {}
    for key, value in data.items():
        keys = key.split(".")
        current_dict = result
        for i, key_part in enumerate(keys):
            if key_part not in current_dict:
                if i == len(keys) - 1:
                    current_dict[key_part] = value
                else:
                    current_dict[key_part] = {}
            current_dict = current_dict[key_part]
    return result


def recursively_get_attr(obj: Any, keys: List[str]):
    return reduce(
        lambda d, key: getattr(d, key),
        keys,
        obj,
    )


def recursively_get_item(obj: Dict[str, Any], keys: List[str]):
    return reduce(
        lambda d, key: d.get(key) if isinstance(d, dict) else None,
        keys,
        obj,
    )
