from enum import Enum, unique
from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Integer,
    ForeignKey,
    String,
    Date,
    Enum as pgEnum,
    ForeignKeyConstraint,
)


# Naming Convention for tables and constraints
convention = {
    "all_column_names": lambda constraint, table: "_".join(
        [column.name for column in constraint.columns.values()]
    ),
    # index naming
    "ix": "ix__%(table_name)s_%(all_column_names)s",
    # unique index naming
    "uq": "uq__%(table_name)s_%(all_column_names)s",
    # check constraints naming
    "ck": "ck__%(table_name)s_%(constarint_name)s",
    # foreign key constraint naming
    "fk": "fk__%(table_name)s_%(all_column_names)s_%(reffered_table_name)s",
    # primary key constraint naming
    "pk": "pk__%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


@unique
class Gender(Enum):
    male = "male"
    female = "female"


import_table = Table("import", metadata, Column("import_id", Integer, primary_key=True))

citizen_table = Table(
    "citizen",
    metadata,
    Column("import_id", Integer, ForeignKey("import.import_id"), primary_key=True),
    Column("citizen_id", Integer, primary_key=True),
    Column("name", String, nullable=False),
    Column("birth_date", Date, nullable=False),
    Column("gender", pgEnum(Gender, name="gender"), nullable=False),
    Column("town", String, nullable=False, index=True),
    Column("street", String, nullable=False),
    Column("building", String, nullable=False),
    Column("apartment", Integer, nullable=False),
)

relation_table = Table(
    "relation",
    metadata,
    Column("import_id", Integer, primary_key=True),
    Column("citizen_id", Integer, primary_key=True),
    Column("relative_id", Integer, primary_key=True),
    ForeignKeyConstraint(
        ("import_id", "citizen_id"),
        ("citizen.import_id", "citizen.citizen_id"),
    ),
    ForeignKeyConstraint(
        ("import_id", "relative_id"),
        ("citizen.import_id", "citizen.citizen_id"),
    ),
)
