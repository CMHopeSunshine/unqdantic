import json
from typing import Any, ClassVar, Dict, List, Optional, Type, TYPE_CHECKING, Union
from typing_extensions import dataclass_transform, Self

from .core import Collection, Database
from .expression import Expression, ExpressionField
from .meta import MetaConfig, mix_meta_config
from .utils import generate_dict, merge_dicts, recursively_get_attr

from pydantic.fields import Field, FieldInfo, ModelField
from pydantic.main import BaseModel, ModelMetaclass


def add_fields(model: Type["Document"], **field_definitions: Any):
    """https://github.com/pydantic/pydantic/issues/1937"""
    new_fields: Dict[str, ModelField] = {}
    new_annotations: Dict[str, Optional[type]] = {}

    for f_name, f_def in field_definitions.items():
        if isinstance(f_def, tuple):
            try:
                f_annotation, f_value = f_def
            except ValueError as e:
                raise ValueError(
                    (
                        "field definitions should either be a tuple of (<type>,"
                        " <default>) or just a default value, unfortunately this means"
                        " tuples as default values are not allowed"
                    ),
                ) from e
        else:
            f_annotation, f_value = None, f_def

        if f_annotation:
            new_annotations[f_name] = f_annotation

        new_fields[f_name] = ModelField.infer(
            name=f_name,
            value=f_value,
            annotation=f_annotation,
            class_validators=None,
            config=model.__config__,
        )

    model.__fields__.update(new_fields)
    model.__annotations__.update(new_annotations)


@dataclass_transform(kw_only_default=True, field_specifiers=(Field, FieldInfo))
class MetaDocument(ModelMetaclass):
    def __new__(
        cls,
        cname: str,
        bases: tuple[type[Any], ...],
        attrs: dict[str, Any],
        **kwargs: Any,
    ):
        meta = MetaConfig

        for base in reversed(bases):
            if base != BaseModel and issubclass(base, Document):
                meta = mix_meta_config(base.meta, MetaConfig)

        allowed_meta_kwargs = {
            key
            for key in dir(meta)
            if not (key.startswith("__") and key.endswith("__"))
        }
        meta_kwargs = {
            key: kwargs.pop(key) for key in kwargs.keys() & allowed_meta_kwargs
        }

        attrs["meta"] = mix_meta_config(attrs.get("Meta"), meta, **meta_kwargs)

        new_cls: Type[Document] = super().__new__(cls, cname, bases, attrs, **kwargs)

        for name, field in new_cls.__fields__.items():
            setattr(new_cls, name, ExpressionField(field, []))

        id_value = Field(
            default_factory=new_cls._generate_id,
            allow_mutation=True,
            init=False,
            unqlite_pk=True,
        )
        add_fields(new_cls, id=(int, id_value))

        new_cls.collection = None
        if new_cls.meta.db is not None:
            new_cls.meta.db.init_model(new_cls)

        return new_cls


@dataclass_transform(kw_only_default=True, field_specifiers=(Field, FieldInfo))
class MetaEmbeddedDocument(ModelMetaclass):
    def __new__(
        cls,
        name: str,
        bases: tuple[type[Any], ...],
        attrs: dict[str, Any],
        **kwargs: Any,
    ):
        new_cls = super().__new__(cls, name, bases, attrs, **kwargs)
        for name, field in new_cls.__fields__.items():
            setattr(new_cls, name, ExpressionField(field, []))
        return new_cls


class Document(BaseModel, metaclass=MetaDocument):
    if TYPE_CHECKING:
        meta: ClassVar[Type[MetaConfig]]
        collection: ClassVar[Optional[Collection]]

        def __init_subclass__(
            cls,
            *,
            name: Optional[str] = None,
            db: Union[Database, str, None] = None,
            **kwargs: Any,
        ) -> None:
            ...

    Meta = MetaConfig

    def insert(self) -> Self:
        if self.collection is None:
            raise ValueError(f"文档 {self.__class__.__name__} 未绑定数据库")
        id = self.collection.store(self.doc(), return_id=True)
        self.id = id
        return self

    def update(
        self,
        *,
        fields: Optional[Dict[Any, Any]] = None,
        **kwargs: Any,
    ) -> bool:
        if self.collection is None:
            raise ValueError(f"文档 {self.__class__.__name__} 未绑定数据库")
        if fields:
            str_fields = {str(k): v for k, v in fields.items()}
            for field, _value in str_fields.items():
                field_keys = field.split(".")
                setattr(
                    recursively_get_attr(self, field_keys[:-1]),
                    field_keys[-1],
                    _value,
                )
        if kwargs:
            for k, v in kwargs.items():
                setattr(self, k, v)
        return self.collection.update(self.id, self.doc())

    def save(self, **kwargs: Any) -> Self:
        if self.collection is None:
            raise ValueError(f"文档 {self.__class__.__name__} 未绑定数据库")
        existing_doc = self.collection.fetch(self.id)
        if existing_doc:
            self.update(**kwargs)
        else:
            self.insert()
        return self

    def delete(self) -> bool:
        if self.collection is None:
            raise ValueError(f"文档 {self.__class__.__name__} 未绑定数据库")
        return self.collection.delete(self.id)

    @classmethod
    def save_all(cls, *documents: Self) -> bool:
        if cls.collection is None:
            raise ValueError(f"文档 {cls.__name__} 未绑定数据库")
        if documents:
            return cls.collection.store(
                [doc.doc() for doc in documents],
                return_id=False,
            )
        return False

    @classmethod
    def find_all(cls, *filter: Union[Expression, bool]) -> List[Self]:
        if cls.collection is None:
            raise ValueError(f"文档 {cls.__name__} 未绑定数据库")
        if not filter:
            return cls.all()
        expression = Expression.merge(filter)
        data = cls.collection.filter(expression.to_filter_func)
        return [cls.from_doc(doc) for doc in data]

    @classmethod
    def find_one(cls, *filter: Union[Expression, bool]) -> Optional[Self]:
        if not filter:
            return cls.get_by_id(0)
        docs = cls.find_all(*filter)
        return docs[0] if docs else None

    @classmethod
    def get_by_id(cls, id: int) -> Optional[Self]:
        if cls.collection is None:
            raise ValueError(f"文档 {cls.__name__} 未绑定数据库")
        if doc := cls.collection.fetch(id):
            return cls.from_doc(doc)
        return None

    @classmethod
    def delete_by_id(cls, id: int) -> bool:
        if cls.collection is None:
            raise ValueError(f"文档 {cls.__name__} 未绑定数据库")
        return cls.collection.delete(id)

    @classmethod
    def all(cls) -> List[Self]:
        if cls.collection is None:
            raise ValueError(f"文档 {cls.__name__} 未绑定数据库")
        return [cls.from_doc(doc) for doc in cls.collection.all()]

    @classmethod
    def clear(cls, recreate: bool = True) -> None:
        if cls.collection is None:
            raise ValueError(f"文档 {cls.__name__} 未绑定数据库")
        cls.collection.drop()
        if recreate:
            cls.collection.create()

    @classmethod
    def get_or_create(
        cls,
        *filter: Union[Expression, bool],
        defaults: Union[Any, Self, None] = None,
    ) -> Self:
        expression = Expression.merge(filter)
        if model := cls.find_one(expression):
            return model
        default = defaults.doc() if isinstance(defaults, Document) else defaults or {}
        default = generate_dict({str(k): v for k, v in default.items()})
        default = merge_dicts(expression.to_dict(), default)
        return cls(**default).insert()

    @classmethod
    def update_or_create(
        cls,
        *filter: Union[Expression, bool],
        defaults: Union[Any, Self, None] = None,
    ) -> Self:
        expression = Expression.merge(filter)
        default = defaults.doc() if isinstance(defaults, Document) else defaults or {}
        default = generate_dict({str(k): v for k, v in default.items()})
        if model := cls.find_one(expression):
            model.update(**default)
            return model
        default = merge_dicts(expression.to_dict(), default)
        return cls(**default).insert()

    @classmethod
    def export_all_to_dict(cls, **kwargs) -> List[Dict[str, Any]]:
        kwargs["by_alias"] = cls.meta.by_alias
        return [doc.dict(**kwargs) for doc in cls.all()]

    @classmethod
    def bulk_save_from_dict(cls, docs: List[Dict[str, Any]]) -> List[Self]:
        return [cls(**doc).save() for doc in docs]

    def doc(self, **kwargs) -> Dict[str, Any]:
        kwargs["by_alias"] = self.meta.by_alias
        data = self.json(**kwargs)
        return json.loads(data)

    @classmethod
    def from_doc(cls, doc: Dict[str, Any]) -> Self:
        doc["id"] = doc.pop("__id")
        return cls(**doc)

    @classmethod
    def get_last_id(cls) -> int:
        if cls.collection is None:
            raise ValueError(f"文档 {cls.__name__} 未绑定数据库")
        return cls.collection.last_record_id()

    @classmethod
    def _generate_id(cls) -> int:
        try:
            return cls.get_last_id() + 1
        except ValueError:
            return 0

    class Config:
        validate_assignment = True


class EmbeddedDocument(BaseModel, metaclass=MetaEmbeddedDocument):
    class Config:
        validate_assignment = True
