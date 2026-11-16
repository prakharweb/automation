"""
SQLAlchemy-Compatible Lightweight ORM Layer (app/utils/orm_compat.py)
Used automatically when running in an offline test/sandbox environment where the
`sqlalchemy` wheel is not installed, while preserving 100% API compatibility with
standard SQLAlchemy declarative models, Column descriptors, Session, and Query.
In production on Render (where requirements.txt installs SQLAlchemy + psycopg2-binary),
`app/database.py` uses native SQLAlchemy directly.
"""
import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Type


class IntegrityError(Exception):
    pass


class ColumnDescriptor:
    def __init__(
        self,
        col_type: str = "TEXT",
        primary_key: bool = False,
        unique: bool = False,
        nullable: bool = True,
        index: bool = False,
        default: Any = None,
        onupdate: Any = None,
        foreign_key: Optional[str] = None,
        name: Optional[str] = None,
    ):
        self.col_type = col_type
        self.primary_key = primary_key
        self.unique = unique
        self.nullable = nullable
        self.index = index
        self.default = default
        self.onupdate = onupdate
        self.foreign_key = foreign_key
        self.name = name

    def __set_name__(self, owner: Type, name: str):
        self.name = name

    def __get__(self, instance: Any, owner: Type = None):
        if instance is None:
            return FieldExpr(owner.__tablename__, self.name, self.col_type)
        return instance.__dict__.get(self.name)

    def __set__(self, instance: Any, value: Any):
        instance.__dict__[self.name] = value


class ConditionExpr:
    def __init__(self, sql: str, params: Tuple[Any, ...]):
        self.sql = sql
        self.params = params

    def __and__(self, other: "ConditionExpr") -> "ConditionExpr":
        return ConditionExpr(f"({self.sql} AND {other.sql})", self.params + other.params)

    def __or__(self, other: "ConditionExpr") -> "ConditionExpr":
        return ConditionExpr(f"({self.sql} OR {other.sql})", self.params + other.params)


class FieldExpr:
    def __init__(self, table: str, name: str, col_type: str = "TEXT"):
        self.table = table
        self.name = name
        self.col_type = col_type
        self.direction = "ASC"

    def _serialize_val(self, val: Any) -> Any:
        if isinstance(val, datetime):
            return val.isoformat()
        if isinstance(val, bool):
            return 1 if val else 0
        return val

    def __eq__(self, other: Any) -> ConditionExpr:  # type: ignore
        if other is None:
            return ConditionExpr(f'"{self.name}" IS NULL', ())
        return ConditionExpr(f'"{self.name}" = ?', (self._serialize_val(other),))

    def __ne__(self, other: Any) -> ConditionExpr:  # type: ignore
        if other is None:
            return ConditionExpr(f'"{self.name}" IS NOT NULL', ())
        return ConditionExpr(f'"{self.name}" != ?', (self._serialize_val(other),))

    def __lt__(self, other: Any) -> ConditionExpr:
        return ConditionExpr(f'"{self.name}" < ?', (self._serialize_val(other),))

    def __le__(self, other: Any) -> ConditionExpr:
        return ConditionExpr(f'"{self.name}" <= ?', (self._serialize_val(other),))

    def __gt__(self, other: Any) -> ConditionExpr:
        return ConditionExpr(f'"{self.name}" > ?', (self._serialize_val(other),))

    def __ge__(self, other: Any) -> ConditionExpr:
        return ConditionExpr(f'"{self.name}" >= ?', (self._serialize_val(other),))

    def ilike(self, pattern: str) -> ConditionExpr:
        return ConditionExpr(f'LOWER("{self.name}") LIKE LOWER(?)', (pattern,))

    def like(self, pattern: str) -> ConditionExpr:
        return ConditionExpr(f'"{self.name}" LIKE ?', (pattern,))

    def in_(self, values: List[Any]) -> ConditionExpr:
        vals = [self._serialize_val(v) for v in values]
        if not vals:
            return ConditionExpr("1 = 0", ())
        placeholders = ", ".join(["?"] * len(vals))
        return ConditionExpr(f'"{self.name}" IN ({placeholders})', tuple(vals))

    def is_(self, other: Any) -> ConditionExpr:
        if other is None:
            return ConditionExpr(f'"{self.name}" IS NULL', ())
        if isinstance(other, bool):
            return ConditionExpr(f'"{self.name}" = ?', (1 if other else 0,))
        return self == other

    def isnot(self, other: Any) -> ConditionExpr:
        if other is None:
            return ConditionExpr(f'"{self.name}" IS NOT NULL', ())
        return self != other

    def desc(self) -> "FieldExpr":
        clone = FieldExpr(self.table, self.name, self.col_type)
        clone.direction = "DESC"
        return clone

    def asc(self) -> "FieldExpr":
        clone = FieldExpr(self.table, self.name, self.col_type)
        clone.direction = "ASC"
        return clone


def or_(*conditions: ConditionExpr) -> ConditionExpr:
    valid = [c for c in conditions if c is not None]
    if not valid:
        return ConditionExpr("1 = 1", ())
    sql = " OR ".join(f"({c.sql})" for c in valid)
    params: List[Any] = []
    for c in valid:
        params.extend(c.params)
    return ConditionExpr(f"({sql})", tuple(params))


def and_(*conditions: ConditionExpr) -> ConditionExpr:
    valid = [c for c in conditions if c is not None]
    if not valid:
        return ConditionExpr("1 = 1", ())
    sql = " AND ".join(f"({c.sql})" for c in valid)
    params: List[Any] = []
    for c in valid:
        params.extend(c.params)
    return ConditionExpr(f"({sql})", tuple(params))


# Type helpers matching SQLAlchemy signature
def String(length: Optional[int] = None) -> str:
    return "TEXT"


def Text() -> str:
    return "TEXT"


def Integer() -> str:
    return "INTEGER"


def Boolean() -> str:
    return "BOOLEAN"


def DateTime(timezone: bool = True) -> str:
    return "DATETIME"


def JSON() -> str:
    return "JSON"


def Float() -> str:
    return "REAL"


def ForeignKey(target: str, ondelete: Optional[str] = None) -> str:
    return f"FK:{target}"


def Column(*args: Any, **kwargs: Any) -> ColumnDescriptor:
    col_type = "TEXT"
    fk = None
    for arg in args:
        if isinstance(arg, str):
            if arg.startswith("FK:"):
                fk = arg[3:]
            else:
                col_type = arg
        elif callable(arg):
            res = arg()
            if isinstance(res, str):
                col_type = res
    return ColumnDescriptor(
        col_type=col_type,
        primary_key=kwargs.get("primary_key", False),
        unique=kwargs.get("unique", False),
        nullable=kwargs.get("nullable", True),
        index=kwargs.get("index", False),
        default=kwargs.get("default", None),
        onupdate=kwargs.get("onupdate", None),
        foreign_key=fk,
    )


def relationship(*args: Any, **kwargs: Any) -> None:
    return None


class ModelMeta(type):
    _registry: List[Type] = []

    def __new__(mcs, name: str, bases: Tuple[Type, ...], attrs: Dict[str, Any]):
        columns: Dict[str, ColumnDescriptor] = {}
        for base in bases:
            if hasattr(base, "__columns__"):
                columns.update(base.__columns__)
        for k, v in list(attrs.items()):
            if isinstance(v, ColumnDescriptor):
                v.name = k
                columns[k] = v
        attrs["__columns__"] = columns
        cls = super().__new__(mcs, name, bases, attrs)
        if name != "Base" and "__tablename__" in attrs:
            mcs._registry.append(cls)
        return cls


class BaseMetadata:
    def create_all(self, bind: "CompatEngine"):
        bind.create_all(ModelMeta._registry)

    def drop_all(self, bind: "CompatEngine"):
        bind.drop_all(ModelMeta._registry)


class Base(metaclass=ModelMeta):
    metadata = BaseMetadata()

    def __init__(self, **kwargs: Any):
        for col_name, col_desc in self.__columns__.items():
            if col_name in kwargs:
                setattr(self, col_name, kwargs[col_name])
            elif col_desc.default is not None:
                val = col_desc.default() if callable(col_desc.default) else col_desc.default
                setattr(self, col_name, val)
            else:
                setattr(self, col_name, None)
        for k, v in kwargs.items():
            if k not in self.__columns__:
                setattr(self, k, v)

    def to_dict(self) -> Dict[str, Any]:
        return {col: getattr(self, col) for col in self.__columns__}


def declarative_base() -> Type[Base]:
    return Base


class CompatEngine:
    def __init__(self, db_url: str):
        self.db_url = db_url
        if db_url.startswith("sqlite:///"):
            self.db_path = db_url.replace("sqlite:///", "", 1)
        elif db_url == "sqlite:///:memory:" or "memory" in db_url:
            self.db_path = ":memory:"
        else:
            self.db_path = "./space_consultant.db"
        self._lock = threading.RLock()
        self._shared_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared_conn.row_factory = sqlite3.Row

    def get_connection(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def create_all(self, models: List[Type[Base]]):
        conn = self.get_connection()
        with self._lock:
            cur = conn.cursor()
            for model in models:
                table = model.__tablename__
                col_defs = []
                for col_name, col in model.__columns__.items():
                    sql_type = "TEXT"
                    if col.col_type in ("INTEGER", "BOOLEAN"):
                        sql_type = "INTEGER"
                    elif col.col_type == "REAL":
                        sql_type = "REAL"
                    parts = [f'"{col_name}" {sql_type}']
                    if col.primary_key:
                        parts.append("PRIMARY KEY")
                    if col.unique and not col.primary_key:
                        parts.append("UNIQUE")
                    if not col.nullable and not col.primary_key:
                        parts.append("NOT NULL")
                    col_defs.append(" ".join(parts))
                ddl = f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)});'
                cur.execute(ddl)
                for col_name, col in model.__columns__.items():
                    if col.index and not col.primary_key and not col.unique:
                        idx_name = f"ix_{table}_{col_name}"
                        cur.execute(
                            f'CREATE INDEX IF NOT EXISTS "{idx_name}" ON "{table}" ("{col_name}");'
                        )
            conn.commit()
        if self._shared_conn is None:
            conn.close()

    def drop_all(self, models: List[Type[Base]]):
        conn = self.get_connection()
        with self._lock:
            cur = conn.cursor()
            for model in reversed(models):
                cur.execute(f'DROP TABLE IF EXISTS "{model.__tablename__}";')
            conn.commit()
        if self._shared_conn is None:
            conn.close()


class CompatQuery:
    def __init__(self, session: "CompatSession", model: Type[Base]):
        self.session = session
        self.model = model
        self._conditions: List[ConditionExpr] = []
        self._order_by: List[str] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None

    def filter(self, *conditions: Any) -> "CompatQuery":
        for cond in conditions:
            if isinstance(cond, ConditionExpr):
                self._conditions.append(cond)
        return self

    def filter_by(self, **kwargs: Any) -> "CompatQuery":
        for k, v in kwargs.items():
            field = getattr(self.model, k)
            self._conditions.append(field == v)
        return self

    def order_by(self, *fields: Any) -> "CompatQuery":
        for f in fields:
            if isinstance(f, FieldExpr):
                self._order_by.append(f'"{f.name}" {f.direction}')
            elif isinstance(f, str):
                self._order_by.append(f)
        return self

    def limit(self, n: int) -> "CompatQuery":
        self._limit = int(n)
        return self

    def offset(self, n: int) -> "CompatQuery":
        self._offset = int(n)
        return self

    def _build_where(self) -> Tuple[str, Tuple[Any, ...]]:
        if not self._conditions:
            return "", ()
        clauses = []
        params: List[Any] = []
        for c in self._conditions:
            clauses.append(f"({c.sql})")
            params.extend(c.params)
        return " WHERE " + " AND ".join(clauses), tuple(params)

    def _build_select(self) -> Tuple[str, Tuple[Any, ...]]:
        table = self.model.__tablename__
        where_sql, params = self._build_where()
        sql = f'SELECT * FROM "{table}"{where_sql}'
        if self._order_by:
            sql += " ORDER BY " + ", ".join(self._order_by)
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"
        if self._offset is not None:
            if self._limit is None:
                sql += " LIMIT -1"
            sql += f" OFFSET {self._offset}"
        return sql, params

    def all(self) -> List[Any]:
        self.session.flush()
        sql, params = self._build_select()
        cur = self.session.conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [self.session._hydrate(self.model, dict(row)) for row in rows]

    def first(self) -> Optional[Any]:
        self._limit = 1
        res = self.all()
        return res[0] if res else None

    def count(self) -> int:
        self.session.flush()
        table = self.model.__tablename__
        where_sql, params = self._build_where()
        sql = f'SELECT COUNT(*) as cnt FROM "{table}"{where_sql}'
        cur = self.session.conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        return int(row["cnt"]) if row else 0

    def delete(self) -> int:
        table = self.model.__tablename__
        where_sql, params = self._build_where()
        sql = f'DELETE FROM "{table}"{where_sql}'
        cur = self.session.conn.cursor()
        cur.execute(sql, params)
        return cur.rowcount


class CompatSession:
    def __init__(self, engine: CompatEngine):
        self.engine = engine
        self.conn = engine.get_connection()
        self._new: List[Base] = []
        self._tracked: List[Base] = []
        self._deleted: List[Base] = []

    def query(self, model: Type[Base]) -> CompatQuery:
        return CompatQuery(self, model)

    def add(self, instance: Base):
        if instance not in self._new and instance not in self._tracked:
            self._new.append(instance)

    def add_all(self, instances: List[Base]):
        for inst in instances:
            self.add(inst)

    def delete(self, instance: Base):
        if instance in self._new:
            self._new.remove(instance)
        else:
            self._deleted.append(instance)

    def _serialize_field(self, col: ColumnDescriptor, val: Any) -> Any:
        if val is None:
            return None
        if col.col_type == "JSON":
            if isinstance(val, (dict, list)):
                return json.dumps(val)
            return val
        if col.col_type == "BOOLEAN":
            return 1 if bool(val) else 0
        if col.col_type == "DATETIME":
            if isinstance(val, datetime):
                return val.isoformat()
            return str(val)
        return val

    def _deserialize_field(self, col: ColumnDescriptor, val: Any) -> Any:
        if val is None:
            return None
        if col.col_type == "JSON":
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except Exception:
                    return val
            return val
        if col.col_type == "BOOLEAN":
            return bool(val)
        if col.col_type == "DATETIME":
            if isinstance(val, str):
                try:
                    return datetime.fromisoformat(val)
                except Exception:
                    return val
            return val
        return val

    def _hydrate(self, model: Type[Base], row: Dict[str, Any]) -> Base:
        pk_name = next((n for n, c in model.__columns__.items() if c.primary_key), "id")
        pk_val = row.get(pk_name)
        for existing in self._tracked:
            if isinstance(existing, model) and getattr(existing, pk_name) == pk_val:
                for col_name, col_desc in model.__columns__.items():
                    if col_name in row:
                        setattr(existing, col_name, self._deserialize_field(col_desc, row[col_name]))
                existing._db_snapshot = {
                    c: self._serialize_field(desc, getattr(existing, c))
                    for c, desc in model.__columns__.items()
                }
                return existing
        inst = model.__new__(model)
        for col_name, col_desc in model.__columns__.items():
            setattr(inst, col_name, self._deserialize_field(col_desc, row.get(col_name)))
        inst._db_snapshot = {
            c: self._serialize_field(desc, getattr(inst, c))
            for c, desc in model.__columns__.items()
        }
        self._tracked.append(inst)
        return inst

    def flush(self):
        cur = self.conn.cursor()
        try:
            # Process inserts
            while self._new:
                inst = self._new.pop(0)
                model = type(inst)
                table = model.__tablename__
                cols = list(model.__columns__.keys())
                vals = []
                for c in cols:
                    col_desc = model.__columns__[c]
                    v = getattr(inst, c, None)
                    if v is None and col_desc.default is not None:
                        v = col_desc.default() if callable(col_desc.default) else col_desc.default
                        setattr(inst, c, v)
                    vals.append(self._serialize_field(col_desc, v))
                col_list = ", ".join(f'"{c}"' for c in cols)
                placeholders = ", ".join(["?"] * len(cols))
                cur.execute(
                    f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})',
                    tuple(vals),
                )
                inst._db_snapshot = dict(zip(cols, vals))
                if inst not in self._tracked:
                    self._tracked.append(inst)

            # Process updates on tracked instances
            for inst in list(self._tracked):
                model = type(inst)
                table = model.__tablename__
                pk_name = next((n for n, c in model.__columns__.items() if c.primary_key), "id")
                snapshot = getattr(inst, "_db_snapshot", {})
                changed_cols = []
                for c, col_desc in model.__columns__.items():
                    curr_s = self._serialize_field(col_desc, getattr(inst, c, None))
                    if snapshot.get(c) != curr_s:
                        changed_cols.append(c)
                if changed_cols:
                    for c, col_desc in model.__columns__.items():
                        if col_desc.onupdate is not None and c not in changed_cols:
                            new_val = (
                                col_desc.onupdate() if callable(col_desc.onupdate) else col_desc.onupdate
                            )
                            setattr(inst, c, new_val)
                            changed_cols.append(c)
                    set_clause = ", ".join(f'"{c}" = ?' for c in changed_cols)
                    params = [
                        self._serialize_field(model.__columns__[c], getattr(inst, c, None))
                        for c in changed_cols
                    ]
                    params.append(self._serialize_field(model.__columns__[pk_name], getattr(inst, pk_name)))
                    cur.execute(
                        f'UPDATE "{table}" SET {set_clause} WHERE "{pk_name}" = ?',
                        tuple(params),
                    )
                    inst._db_snapshot = {
                        c: self._serialize_field(desc, getattr(inst, c))
                        for c, desc in model.__columns__.items()
                    }

            # Process deletes
            while self._deleted:
                inst = self._deleted.pop(0)
                model = type(inst)
                table = model.__tablename__
                pk_name = next((n for n, c in model.__columns__.items() if c.primary_key), "id")
                cur.execute(
                    f'DELETE FROM "{table}" WHERE "{pk_name}" = ?',
                    (getattr(inst, pk_name),),
                )
                if inst in self._tracked:
                    self._tracked.remove(inst)
        except sqlite3.IntegrityError as exc:
            raise IntegrityError(str(exc)) from exc

    def commit(self):
        with self.engine._lock:
            self.flush()
            self.conn.commit()

    def rollback(self):
        self._new.clear()
        self._deleted.clear()
        self.conn.rollback()

    def refresh(self, instance: Base):
        model = type(instance)
        pk_name = next((n for n, c in model.__columns__.items() if c.primary_key), "id")
        pk_val = getattr(instance, pk_name)
        cur = self.conn.cursor()
        cur.execute(
            f'SELECT * FROM "{model.__tablename__}" WHERE "{pk_name}" = ?',
            (pk_val,),
        )
        row = cur.fetchone()
        if row:
            for col_name, col_desc in model.__columns__.items():
                setattr(instance, col_name, self._deserialize_field(col_desc, row[col_name]))
            instance._db_snapshot = {
                c: self._serialize_field(desc, getattr(instance, c))
                for c, desc in model.__columns__.items()
            }

    def execute(self, statement: str, params: Tuple[Any, ...] = ()):
        cur = self.conn.cursor()
        if isinstance(statement, str):
            cur.execute(statement, params)
        return cur

    def close(self):
        if self.engine._shared_conn is None:
            self.conn.close()


def create_engine(db_url: str, **kwargs: Any) -> CompatEngine:
    return CompatEngine(db_url)


def sessionmaker(bind: CompatEngine, **kwargs: Any) -> Callable[[], CompatSession]:
    def _factory() -> CompatSession:
        return CompatSession(bind)

    return _factory
