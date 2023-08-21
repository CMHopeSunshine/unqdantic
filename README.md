<p align="center">
    <h1 align="center">UnqDantic</h1>
    <p align="center">基于 UnQLite 的嵌入式数据库 ODM</p>
</p>
<p align="center">
    <a href="./LICENSE">
        <img src="https://img.shields.io/github/license/CMHopeSunshine/unqdantic.svg" alt="license">
    </a>
    <a href="https://pypi.python.org/pypi/unqdantic">
        <img src="https://img.shields.io/pypi/v/unqdantic.svg" alt="pypi">
    </a>
    <a href="https://www.python.org/">
        <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="python">
    </a>
</p>

## 简介

UnqDantic 是一个基于 [UnQLite](https://github.com/symisc/unqlite) 和 [Pydantic](https://pydantic-docs.helpmanual.io/) 的 Python 对象文档映射器(ODM)。

基于 UnQLite 的轻量、嵌入式特性，你可以在单文件或者内存中使用 NoSQL 数据库，就像 mongodb 一样！

得益于 Pydantic 的模型和数据验证，你可以轻松的构建一个文档模型，非常简单高效地创建和查询数据！

在简单的场景下，它完全可以替代复杂的 mongodb，让你更加高效方便地存储 JSON 文档数据。

**不要再用 json 文件当数据库用啦，来试试 UnqDantic 吧！！**

> 但是 UNQlite 不支持索引、唯一约束等特性，尚未知性能如何，可能不适用于大型项目

## 安装

> 注意，本库还在开发中，后续可能会有 breaking change，谨慎使用

- 使用 pip: `pip install unqdantic`
- 使用 Poetry: `poetry add unqdantic`
- 使用 PDM: `pdm add unqdantic`

## 示例

```python
from typing import Any, Dict, List, Optional

from unqdantic import Database, Document, EmbeddedDocument

from pydantic import Field


# 像pydantic一样定义模型，可以使用pydantic的所有特性
# 定义内嵌模型
class UserInfo(EmbeddedDocument):
    money: int = 100
    level: int = 1


# 定义文档模型
class User(Document):
    name: str
    age: int
    info: UserInfo = Field(default_factory=UserInfo)


# 初始化unqlite数据库
# filename中，:mem:代表在内存中使用，也可以传入文件路径
# documents为要绑定的文档模型，数据库会自动为模型创建同名的集合
db = Database(filename=":mem:", documents=[User])
# db = Database(filename=pathlib.Path("my_data.db"), documents=[User])

# 使用Pydantic式创建文档对象，调用insert()来插入文档
user1 = User(name="a", age=15).insert()

# 更新模型对象的属性，并更新到数据库
user1.update(
    fields={
        User.age: 20,
        User.info.money: 150,
    },
)
# 也可以用关键字参数形式更新
# user1.update(age=20)

# 还可以手动修改后，调用save()来更新到数据库
user1.info.level = 2
user1.save()

# 删除该文档
user1.delete()

# 如果没有name为a且age为15的文档，则创建，否则更新info.level为2
user2 = User.update_or_create(
    User.name == "a",
    User.age == 20,
    defaults={
        User.info.level: 2,
    },
)
# 这两个模型的id一致
assert user1.id == user2.id

# 可以先创建模型对象，然后使用save_all批量插入到数据库
user3 = User(name="b", age=18, info=UserInfo(money=150))
user4 = User(name="c", age=25, info=UserInfo(money=200, level=20))
User.save_all(user3, user4)

# 如果没有name为d的文档，则使用defaults中的数据创建它，否则获取它
user5 = User.get_or_create(
    User.name == "d",
    defaults={
        User.age: 15,
        User.info.level: 10,
    },
)

# 根据主键id查询文档
user: Optional[User] = User.get_by_id(id=0)
# 根据主键id删除文档
delete_result: bool = User.delete_by_id(id=0)

# 查询满足所有条件的文档
users: List[User] = User.find_all(User.age == 18, User.info.money >= 150)
# 查询满足任一条件的文档
users: List[User] = User.find_all((User.age <= 18) | (User.info.level >= 2))
# 查询满足条件的首个文档，如无则返回None
user: Optional[User] = User.find_one(User.age >= 18)

# 取出所有文档
all_users: List[User] = User.all()
# 导出所有文档为dict对象
user_dicts: List[Dict[str, Any]] = User.export_all_to_dict()
# 从Dict对象列表批量保存文档
users: List[User] = User.bulk_save_from_dict(user_dicts)
# 清空所有文档
User.clear()


# 如果你不想使用文档模型，也可以直接操作集合
from unqdantic import Collection

# 需要传入数据库对象和集合名
collection = Collection(db=db, name="custom_collection")
# 可以存放任意dict或List[dict]，但是要注意：
# 值只支持str、int、float、bool等基本数据类型，复杂类型可能会被存为None
# 返回结果为最后一个文档的主键id
id: int = collection.store({"key": "value"})
id: int = collection.store([{"name": "a"}, {"name": "b", "age": 18}])
# 获取指定id的文档
data: Optional[Dict[str, Any]] = collection.fetch(id=id)
# 更新指定id的文档
# 注意，它不等于dict.update，它是完全替换旧的文档内容
collection.update(id=id, data={"key": "value2"})
# 删除文档
collection.delete(id=id)

# 可以过滤查询文档
# 需要传入一个参数为文档，返回值为bool的函数
datas: List[Dict[str, Any]] = collection.filter(lambda doc: doc["name"] == "a")

# 除此之外，你还可以直接将数据库db当键值对数据库使用，就像python的dict一样
# 但是同样的，值只支持基本数据类型，并且返回值是该值的bytes形式

# 存一个键值对
db["key"] = "value"
# 取出值
value: Optional[bytes] = db["key"]  # b"value"
# 删除值
del db["key"]
# 查看键值对是否存在
assert "key" not in db
```

## 后续计划

- [ ] 允许自定义encoder、decoder
- [ ] 复杂的事务支持
- [ ] Async IO 支持(也许不会)

## 鸣谢

- [UnQLite](https://github.com/symisc/unqlite): 本项目的基础， C 语言编写的嵌入式 NoSQL 文档数据库
- [unqlite-python](https://github.com/coleifer/unqlite-python)：本项目的基础，unqlite 的 python binding
- [Pydantic](https://pydantic-docs.helpmanual.io/): 本项目的基础，数据模型检验库
- [mango](https://github.com/A-kirami/mango): odm 代码参考
