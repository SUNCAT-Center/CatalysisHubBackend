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
    #'sqlite:///database/catapp.db',
    #'postgres:///catapp',
    'postgres://lotoqewsbqixgj:bcd5ae5d07fbe87fa416bbfc26c0442fa8b91a1eabfbcd33bb5c9bd00bcb460d@ec2-54-221-229-64.compute-1.amazonaws.com:5432/d2jm87f56r69bn',
    convert_unicode=True)

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
    #rowid = sqlalchemy.Column(sqlalchemy.Integer)
    chemical_composition = Column(String, )
    surface_composition = Column(String, )
    facet = Column(String, )
    sites = Column(String, )
    reactants = Column(String, )
    products = Column(String, )
    reaction_energy = Column(Float, )
    activation_energy = Column(Float, )
    dft_code = Column(String, )
    dft_functional = Column(String, )
    reference = Column(String, )
    doi = Column(String, )
    year = Column(Integer, )
    ase_ids = Column(String, )
