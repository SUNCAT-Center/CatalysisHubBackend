# global imports
import os
import sqlalchemy
import sqlalchemy.types
import sqlalchemy.ext.declarative
from sqlalchemy import or_
from sqlalchemy.dialects.postgresql import JSONB
import graphene.types.json
try:
    import io as StringIO
except:
    # Fallback solution for python2.7
    import StringIO

import numpy as np

import json
import sqlalchemy as sqla
from sqlalchemy.ext import mutable
from sqlalchemy.ext.hybrid import hybrid_property

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

url = sqlalchemy.engine.url.URL('postgres',
                                username='catappuser',
                                password=os.environ['DB_PASSWORD'],
                                host='catappdatabase.cjlis1fysyzx.us-west-1.rds.amazonaws.com',
                                port=5432,
                                database='catappdatabase')


engine = sqlalchemy.create_engine(
    url,
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
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    #rowid = sqlalchemy.sqlalchemy.Column(sqlalchemy.Integer)
    chemical_composition = sqlalchemy.Column(sqlalchemy.String, )
    surface_composition = sqlalchemy.Column(sqlalchemy.String, )
    facet = sqlalchemy.Column(sqlalchemy.String, )
    sites = sqlalchemy.Column(sqlalchemy.String, )
    reactants = sqlalchemy.Column(JSONB, )
    products = sqlalchemy.Column(JSONB, )
    reaction_energy = sqlalchemy.Column(sqlalchemy.Float, )
    activation_energy = sqlalchemy.Column(sqlalchemy.Float, )
    dft_code = sqlalchemy.Column(sqlalchemy.String, )
    dft_functional = sqlalchemy.Column(sqlalchemy.String, )
    publication = sqlalchemy.Column(JSONB, )
    doi = sqlalchemy.Column(sqlalchemy.String, )
    year = sqlalchemy.Column(sqlalchemy.Integer, )
    ase_ids = sqlalchemy.Column(JSONB, )

    @hybrid_property
    def _publication_title(self):
        return self.publication['title']
    
    @hybrid_property
    def _publication_publisher(self):
        return self.publication['publisher']
    
    @hybrid_property
    def _publication_journal(self):
        return self.publication['journal']
    
    @hybrid_property
    def _publication_volume(self):
        return self.publication['volume']
    
    @hybrid_property
    def _publication_number(self):
        return self.publication['number']
    
    @hybrid_property
    def _publication_authors(self):
        return self.publication['authors']
    
    @hybrid_property
    def _publication_doi(self):
        return self.publication['doi']
    
    @hybrid_property
    def _publication_year(self):
        return self.publication['year']
    
    @hybrid_property
    def _publication_pages(self):
        return self.publication['pages']

    @hybrid_property
    def _reaction(self):
        reaction = ''
        arrow = 0
        for column in (self.reactants, self.products):
            if arrow == 1:
                reaction += ' -> '
            arrow += 1
            i = 0
            for key in sorted(column, key=len, reverse=True):
                prefactor = column[key][1]
                state = column[key][0]
                if state == 'gas':
                    state = '(g)'
                if state == 'star':
                    state = '*'
                if not i == 0:
                    if prefactor > 0:
                        reaction += ' + '
                    else:
                        reaction += ' - '
                        prefactor *= -1
                if prefactor == 1:
                    prefactor = ''

                reaction += str(prefactor) + key + state
                i += 1
        return reaction

class Information(Base):
    __tablename__ = 'information'
    name = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
    value = sqlalchemy.Column(sqlalchemy.String, )


class System(Base):
    __tablename__ = 'systems'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    #rowid = sqlalchemy.Column(sqlalchemy.Integer, )
    unique_id = sqlalchemy.Column(sqlalchemy.String, )
    ctime = sqlalchemy.Column(sqlalchemy.Float, )
    mtime = sqlalchemy.Column(sqlalchemy.Float, )
    username = sqlalchemy.Column(sqlalchemy.String)
    numbers = sqlalchemy.Column(sqlalchemy.types.String, )  # BLOB
    positions = sqlalchemy.Column(sqlalchemy.types.String, )  # BLOB
    cell = sqlalchemy.Column(sqlalchemy.String)  # BLOB
    pbc = sqlalchemy.Column(sqlalchemy.Integer,)
    initial_magmoms = sqlalchemy.Column(sqlalchemy.Integer,)  # BLOB,
    initial_charges = sqlalchemy.Column(sqlalchemy.Integer,)  # BLOB,
    masses = sqlalchemy.Column(sqlalchemy.Integer,)  # BLOB,
    tags = sqlalchemy.Column(sqlalchemy.String, )  # BLOBS
    momenta = sqlalchemy.Column(sqlalchemy.String, )  # BLOB,
    constraints = sqlalchemy.Column(sqlalchemy.String, )  # BLOB
    calculator = sqlalchemy.Column(sqlalchemy.String, )
    calculator_parameters = sqlalchemy.Column(sqlalchemy.String, )
    energy = sqlalchemy.Column(sqlalchemy.Float, )
    free_energy = sqlalchemy.Column(sqlalchemy.Float, )
    forces = sqlalchemy.Column(sqlalchemy.String)  # BLOB
    stress = sqlalchemy.Column(sqlalchemy.String)  # BLOB
    dipole = sqlalchemy.Column(sqlalchemy.String)  # BLOB
    magmoms = sqlalchemy.Column(sqlalchemy.String)  # BLOB
    magmom = sqlalchemy.Column(sqlalchemy.Float, )
    charges = sqlalchemy.Column(sqlalchemy.String)  # BLOB
    key_value_pairs = sqlalchemy.Column(sqlalchemy.String, )
    data = sqlalchemy.Column(sqlalchemy.String,)
    natoms = sqlalchemy.Column(sqlalchemy.Integer,)
    fmax = sqlalchemy.Column(sqlalchemy.Float, )
    smax = sqlalchemy.Column(sqlalchemy.Float, )
    volume = sqlalchemy.Column(sqlalchemy.Float, )
    mass = sqlalchemy.Column(sqlalchemy.Float, )
    charge = sqlalchemy.Column(sqlalchemy.Float, )
    keys = sqlalchemy.orm.relationship("Key", backref="systems", uselist=True)

    species = sqlalchemy.orm.relationship(
        "Species", backref="systems", uselist=True)
    text_keys = sqlalchemy.orm.relationship(
        "TextKeyValue", backref="systems", uselist=True)
    number_keys = sqlalchemy.orm.relationship(
        "NumberKeyValue", backref="systems", uselist=True)

    ###################################
    # GENERAL ATOMS FORMATS
    ###################################
    def _toatoms(self):
        positions = ase.db.sqlite.deblob(self.positions).reshape(-1, 3)
        numbers = ase.db.sqlite.deblob(self.numbers, np.int32)
        cell = ase.db.sqlite.deblob(self.cell).reshape(-1, 3)

        return ase.atoms.Atoms(
            numbers,
            positions,
            cell=cell,
            pbc=(self.pbc & np.array([1, 2, 4])).astype(bool),
        )

    @hybrid_property
    def _cifdata(self):
        mem_file = StringIO.StringIO()
        ase.io.write(mem_file, self._toatoms(), 'cif')

        return mem_file.getvalue()

    ###################################
    # UNPACKED ASE-DB BLOB FIELDS
    ###################################
    @hybrid_property
    def _numbers(self):
        return (ase.db.sqlite.deblob(self.numbers, np.int32).tolist())

    @hybrid_property
    def _positions(self):
        return json.dumps(
            ase.db.sqlite.deblob(self.positions).reshape(-1, 3).tolist()
        )

    @hybrid_property
    def _cell(self):
        return (ase.db.sqlite.deblob(self.cell).reshape(-1, 3).tolist())

    @hybrid_property
    def _pbc(self):
        return (self.pbc & np.array([1, 2, 4])).astype(bool).tolist()

    @hybrid_property
    def _initial_magmoms(self):
        return ase.db.sqlite.deblob(self.initial_magmoms)

    @hybrid_property
    def _initial_charges(self):
        return ase.db.sqlite.deblob(self.initial_charges)

    @hybrid_property
    def _masses(self):
        return ase.db.sqlite.deblob(self.masses)

    @hybrid_property
    def _tags(self):
        return ase.db.sqlite.deblob(self.tags, np.int32)

    @hybrid_property
    def _momenta(self):
        return ase.db.sqlite.deblob(self.moment, shape=(-1, 3))

    @hybrid_property
    def _forces(self):
        return ase.db.sqlite.deblob(self.forces, shape=(-1, 3))

    @hybrid_property
    def _stress(self):
        return ase.db.sqlite.deblob(self.stress)

    @hybrid_property
    def _dipole(self):
        return ase.db.sqlite.deblob(self.dipole)

    @hybrid_property
    def _magmoms(self):
        return (ase.db.sqlite.deblob(self.magmoms).tolist())

    @hybrid_property
    def _charges(self):
        return (ase.db.sqlite.deblob(self.charges).tolist())

    ###################################
    # PUBLICATION METADATA
    ###################################
    @hybrid_property
    def _publication_doi(self):
        return json.loads(self.key_value_pairs).get('publication_doi', '')

    @hybrid_property
    def _publication_year(self):
        return json.loads(self.key_value_pairs).get('publication_year', '')

    @hybrid_property
    def _publication_authors(self):
        return json.loads(self.key_value_pairs).get('publication_authors', '')

    @hybrid_property
    def _publication_title(self):
        return json.loads(self.key_value_pairs).get('publication_title', '')

    @hybrid_property
    def _publication_journal(self):
        return json.loads(self.key_value_pairs).get('publication_journal', '')

    @hybrid_property
    def _publication_pages(self):
        return json.loads(self.key_value_pairs).get('publication_pages', '')

    @hybrid_property
    def _publication_year(self):
        return json.loads(self.key_value_pairs).get('publication_year', '')

    @hybrid_property
    def _publication_volume(self):
        return json.loads(self.key_value_pairs).get('publication_volume', '')

    @hybrid_property
    def _publication_number(self):
        return json.loads(self.key_value_pairs).get('publication_number', '')

    @hybrid_property
    def _publication_url(self):
        return json.loads(self.key_value_pairs).get('publication_url', '')

    ###################################
    # CATAPP-DB STANDARD FIELDS
    ###################################
    @hybrid_property
    def _reaction(self):
        reaction = json.loads(self.key_value_pairs).get('reaction', '')
        reaction = reaction.replace('__', '->').replace('_', '+')
        return reaction

    @hybrid_property
    def _username(self):
        return json.loads(self.key_value_pairs).get('username', '')

    @hybrid_property
    def _adsorbate(self):
        return json.loads(self.key_value_pairs).get('adsorbate', '')

    @hybrid_property
    def _substrate(self):
        return json.loads(self.key_value_pairs).get('substrate', '')

    @hybrid_property
    def _facet(self):
        return json.loads(self.key_value_pairs).get('facet', '').strip("()")

    @hybrid_property
    def _dft_code(self):
        return json.loads(self.key_value_pairs).get('dft_code', '')

    @hybrid_property
    def _dft_functional(self):
        return json.loads(self.key_value_pairs).get('dft_functional', '')


    ###################################
    # OTHER CALCULATED FIELDS
    ###################################
    @hybrid_property
    def _formula(self):
        return self._toatoms().get_chemical_formula()


class Species(Base):
    __tablename__ = 'species'
    id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey(
        'systems.id'), primary_key=True)
    #rowid = sqlalchemy.Column(sqlalchemy.Integer, )
    Z = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True,)
    n = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True,)


class Key(Base):
    __tablename__ = 'keys'
    id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey(
        'systems.id'), primary_key=True)
    #rowid = sqlalchemy.Column(sqlalchemy.Integer, )
    key = sqlalchemy.Column(sqlalchemy.String, primary_key=True)


class NumberKeyValue(Base):
    __tablename__ = 'number_key_values'
    id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey(
        'systems.id'), primary_key=True)
    #rowid = sqlalchemy.Column(sqlalchemy.Integer, )
    key = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
    value = sqlalchemy.Column(sqlalchemy.Float,)


class TextKeyValue(Base):
    __tablename__ = 'text_key_values'
    id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey(
        'systems.id'), primary_key=True)
    #rowid = sqlalchemy.Column(sqlalchemy.Integer, )
    key = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
    value = sqlalchemy.Column(sqlalchemy.String,)
