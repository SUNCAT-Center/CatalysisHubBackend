# global imports
import sqlalchemy
import sqlalchemy.types
import sqlalchemy.ext.declarative
import graphene.types.json
try:
    import io as StringIO
except:
    import StringIO

import numpy as np

import json
import sqlalchemy as sqla
from sqlalchemy.ext import mutable
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import Column, String, Integer, Float

# more unstable imports
import ase.atoms
import ase.db.sqlite
import ase.io


class JsonEncodedDict(sqla.TypeDecorator):
    """Enables JSON storage by encoding and decoding on the fly."""
    impl = sqla.String

    def process_bind_param(self, value, dialect):
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        return json.loads(value)

# set to local database path
engine = sqlalchemy.create_engine(
    'sqlite:///database/catapp.db', convert_unicode=True)

db_session = sqlalchemy.orm.scoped_session(sqlalchemy.orm.sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
))


Base = sqlalchemy.ext.declarative.declarative_base()
Base.query = db_session.query_property()


class Catapp(Base):
    __tablename__ = 'catapp'
    id = Column(Integer, primary_key=True)
    chemical_composition = Column(String, )
    surface_composition = Column(String, )
    facet = Column(String, )
    sites = Column(String, )
    reactants = Column(String, )
    products = Column(String, )
    reaction_energy = Column(Float, )
    activation_energy = Column(Float, )
    DFT_code = Column(String, )
    DFT_functional = Column(String, )
    reference = Column(String, )
    doi = Column(String, )
    year = Column(Integer, )
    reactant_ids = Column(String, ) 
    TS_id = Column(String, )
    product_ids = Column(String, )
    reference_ids = Column(String, )
