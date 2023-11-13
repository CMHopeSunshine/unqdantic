from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Iterable,
    Iterator,
    List,
    Literal,
    Optional,
    overload,
    Set,
    Tuple,
    Type,
    TYPE_CHECKING,
    Union,
)
from typing_extensions import Self

import unqlite

if TYPE_CHECKING:
    from .models import Document
from .types import UnqliteOpenFlag


class Collection:
    def __init__(self, db: "Database", name: str) -> None:
        self.collection: unqlite.Collection = db.db.collection(name)
        if not self.collection.exists():
            self.collection.create()
        self.db: Database = db
        self.name: str = name

    def __repr__(self) -> str:
        return f"Collection(name={self.name})"

    def all(self) -> List[Dict[str, Any]]:
        return self.collection.all()

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        return self.collection.__iter__()

    def __next__(self) -> Dict[str, Any]:
        return self.collection.__next__()

    def __len__(self) -> int:
        return self.collection.__len__()

    def filter(
        self,
        filter_fn: Callable[[Dict[str, Any]], bool],
    ) -> Optional[List[Dict[str, Any]]]:
        return self.collection.filter(filter_fn)

    def create(self) -> bool:
        return self.collection.create()

    def drop(self) -> bool:
        return self.collection.drop()

    def exists(self) -> bool:
        return self.collection.exists()

    def creation_date(self) -> Optional[datetime]:
        date = self.collection.creation_date()
        if isinstance(date, str):
            return datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        return None

    def set_schema(self, schema: Dict[str, Any], **kwargs) -> bool:
        return self.collection.set_schema(schema, **kwargs)

    def get_schema(self) -> Dict[str, Any]:
        return self.collection.get_schema()

    def last_record_id(self) -> int:
        return self.collection.last_record_id()

    def current_record_id(self) -> int:
        return self.collection.current_record_id()

    def reset_cursor(self) -> None:
        self.collection.reset_cursor()

    def fetch(self, id: int) -> Optional[Dict[str, Any]]:
        return self.collection.fetch(id)

    def __getitem__(self, id: int) -> Optional[Dict[str, Any]]:
        return self.collection.fetch(id)

    @overload
    def store(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        return_id: Literal[True] = True,
    ) -> int:
        ...

    @overload
    def store(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        return_id: Literal[False],
    ) -> bool:
        ...

    def store(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        return_id: bool = True,
    ) -> Union[int, bool]:
        return self.collection.store(data, return_id)

    def update(self, id: int, data: Dict[str, Any]) -> bool:
        return self.collection.update(id, data)

    def __setitem__(self, id: int, data: Dict[str, Any]) -> bool:
        return self.collection.update(id, data)

    def delete(self, id: int) -> bool:
        return self.collection.delete(id)

    def __delitem__(self, id: int) -> bool:
        return self.collection.delete(id)

    def fetch_current(self) -> Optional[Dict[str, Any]]:
        return self.collection.fetch_current()


class Database:
    _documents: Set[str] = set()

    def __init__(
        self,
        filename: Union[str, Path] = ":mem:",
        documents: Optional[Iterable[Type["Document"]]] = None,
        flags: UnqliteOpenFlag = UnqliteOpenFlag.CREATE,
        open_database: bool = True,
    ) -> None:
        self.filename: str = (
            str(filename.absolute()) if isinstance(filename, Path) else filename
        )
        self.db: unqlite.UnQLite = unqlite.UnQLite(self.filename, flags, open_database)
        self.collections: Dict[str, Collection] = {}
        if documents:
            for document in documents:
                if document.meta.name not in self._documents:
                    self.init_model(document)
                    self._documents.add(document.meta.name)

    def __repr__(self) -> str:
        return f"Database(filename={self.filename})"

    @property
    def opened(self) -> bool:
        return self.db.is_open

    def init_model(self, model: Type["Document"]):
        model.collection = self.collection(model.meta.name)
        model.meta.db = self
        model.collection.set_schema(model.schema(by_alias=model.meta.by_alias))

    def open(self) -> bool:
        if self.opened:
            return True
        return self.db.open()

    def close(self) -> bool:
        if not self.opened:
            return True
        return self.db.close()

    def __enter__(self) -> Self:
        if not self.opened:
            self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def disable_autocommit(self):
        return self.db.disable_autocommit()

    def store(self, key: str, value: Any) -> None:
        return self.db.store(key, value)

    def __setitem__(self, key: str, value: Any) -> None:
        return self.db.store(key, value)

    def fetch(self, key: str) -> Optional[bytes]:
        try:
            return self.db.fetch(key)
        except KeyError:
            return None

    def __getitem__(self, key: str) -> Optional[bytes]:
        return self.db.fetch(key)

    def delete(self, key: str) -> None:
        return self.db.delete(key)

    def __delitem__(self, key: str) -> None:
        return self.db.delete(key)

    def append(self, key: str, value: Any) -> None:
        return self.db.append(key, value)

    def exists(self, key: str) -> bool:
        return self.db.exists(key)

    def __contains__(self, key: str) -> bool:
        return self.db.exists(key)

    def begin(self) -> bool:
        return self.db.begin()

    def rollback(self) -> bool:
        return self.db.rollback()

    def commit(self) -> bool:
        return self.db.commit()

    def transaction(self) -> unqlite.Transaction:
        return self.db.transaction()

    def commit_on_success(self, func) -> None:
        return self.db.commit_on_success(func)

    def cursor(self) -> unqlite.Cursor:
        return self.db.cursor()

    def vm(self, code: str) -> unqlite.VM:
        return self.db.vm(code)

    def collection(self, name: str) -> Collection:
        if name not in self.collections:
            self.collections[name] = Collection(self, name)
        return self.collections[name]

    def keys(self) -> Generator[str, None, None]:
        return self.db.keys()

    def values(self) -> Generator[bytes, None, None]:
        return self.db.values()

    def items(self) -> Generator[Tuple[str, bytes], None, None]:
        return self.db.items()

    def update(self, data: Dict[str, Any]) -> None:
        self.db.update(data)

    def __iter__(self) -> Iterator[Tuple[str, bytes]]:
        return iter(self.db.items())

    def range(
        self,
        start: str,
        stop: str,
        include_end_key: bool = True,
    ) -> Generator[Tuple[str, bytes], None, None]:
        return self.db.range(start, stop, include_end_key)

    def __len__(self) -> int:
        return self.db.__len__()

    def flush(self):
        self.db.flush()

    def random_string(self, length: int) -> bytes:
        return self.db.random_string(length)

    def random_number(self) -> int:
        return self.db.random_number()

    @property
    def lib_version(self) -> bytes:
        return self.db.lib_version()
