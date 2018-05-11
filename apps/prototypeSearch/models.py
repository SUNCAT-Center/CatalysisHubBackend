# global imports
import os
import json
import sqlalchemy
import sqlalchemy.types
import sqlalchemy.ext.declarative
from sqlalchemy import or_, func, and_, desc
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, ARRAY
from sqlalchemy.dialects import postgresql
from sqlalchemy import Integer, String, Column, Float, Index

SCHEMA = os.environ.get('DB_SCHEMA_FIREWORKS', 'fireworks')


if os.environ.get('DB_PASSWORD_FIREWORKS', ''):
    url = sqlalchemy.engine.url.URL('postgres',
                                    username=os.environ.get(
                                        'DB_USER_FIREWORKS', 'fireworks'),
                                    host=os.environ.get(
                                        'DB_HOST_FIREWORKS',
                                        'catalysishub.c8gwuc8jwb7l.us-west-2.rds.amazonaws.com'),
                                    database=os.environ.get(
                                        'DB_DATABASE_FIREWORKS', 'catalysishub'),
                                    password=os.environ.get(
                                        'DB_PASSWORD_FIREWORKS', ''),
                                    # port=5432,
                                    )
else:
    url = sqlalchemy.engine.url.URL('postgres',
                                    username='postgres',
                                    host='localhost',
                                    #port=5432,
                                    database='travis_ci_test_fireworks')

engine = sqlalchemy.create_engine(
    url,
    convert_unicode=True,
    # echo=True,
)

session = sqlalchemy.orm.scoped_session(sqlalchemy.orm.sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
))

inspector = sqlalchemy.engine.reflection.Inspector.from_engine(
        engine
        )

Base = sqlalchemy.ext.declarative.declarative_base()
Base.query = session.query_property()
metadata = Base.metadata


class Geometry(Base):
    __tablename__ = 'geometry'
    __table_args__ = ({'schema': SCHEMA},)

    repository = Column(String, primary_key=True, index=True)
    spacegroup = Column(Integer, index=True)
    n_atoms = Column(Integer, index=True, nullable=False)
    n_wyckoffs = Column(Integer, index=True, nullable=False)
    wyckoffs = Column(ARRAY(String), index=True, nullable=False)
    n_species = Column(Integer, index=True, nullable=False)
    species = Column(ARRAY(String), index=True, nullable=False)
    n_parameters = Column(Integer, index=True, nullable=False)
    parameter_names = Column(ARRAY(String), nullable=False)
    prototype = Column(String, index=True, nullable=False)
    stoichiometry = Column(String, index=True, nullable=False)
    n_permutations = Column(Integer, index=True, nullable=False)
    # permutations -- skipped for now
    parameters = Column(ARRAY(Float), nullable=False)
    handle = Column(String, index=True, primary_key=True, nullable=False)
    tags = Column(String, index=True)
    scarcity = Column(Float, index=True)
    density = Column(Float, index=True)
    volume = Column(Float, index=True)

    # prototype = sqlalchemy.ForeignKey(SCHEMA + '.prototype.name', index=True)
    permutations = sqlalchemy.Column(sqlalchemy.String, index=True)


class Prototype(Base):
    __tablename__ = 'prototype'
    __table_args__ = {'schema': SCHEMA}

    name = sqlalchemy.Column(
        sqlalchemy.String, primary_key=True, index=True, nullable=False)
    spacegroup = sqlalchemy.Column(
        sqlalchemy.Integer, index=True, nullable=False)
    natom = sqlalchemy.Column(sqlalchemy.Integer, index=True, nullable=False)
    n_wyckoffs = sqlalchemy.Column(
        sqlalchemy.Integer, index=True, nullable=False)
    wyckoffs = sqlalchemy.Column(sqlalchemy.String, index=True, nullable=False)
    n_species = sqlalchemy.Column(
        sqlalchemy.Integer, index=True, nullable=False)
    species = sqlalchemy.Column(sqlalchemy.String, index=True, nullable=False)
    n_parameters = sqlalchemy.Column(
        sqlalchemy.Integer, index=True, nullable=False)
    parameters = sqlalchemy.Column(
        sqlalchemy.String, index=True, nullable=False)
    n_permutations = sqlalchemy.Column(
        sqlalchemy.Integer, index=True, nullable=False)
    permutations = sqlalchemy.Column(sqlalchemy.String, index=True)
