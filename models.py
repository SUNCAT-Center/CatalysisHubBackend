# global imports
import os
import datetime
import sqlalchemy
import sqlalchemy.types
import sqlalchemy.ext.declarative
from sqlalchemy import or_
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, BYTEA
from sqlalchemy import String, Float, Integer
from sqlalchemy.types import ARRAY
from sqlalchemy.ext.associationproxy import association_proxy
import graphene.types.json
try:
    import io as StringIO
except ImportError:
    # Fallback solution for python2.7
    import StringIO

import numpy as np

import json
import sqlalchemy as sqla
from sqlalchemy.ext import mutable
from sqlalchemy.ext.hybrid import hybrid_property

# more unstable imports
import ase.atoms
from ase.constraints import dict2constraint
from ase.calculators.singlepoint import SinglePointCalculator
from ase.calculators.calculator import Calculator
import ase.db.sqlite
import ase.db.core
import ase.io
from ase.utils import formula_metal


class JsonEncodedDict(sqla.TypeDecorator):
    """Enables JSON storage by encoding and decoding on the fly."""


    def process_bind_param(self, value, dialect):
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        return json.loads(value)


SCHEMA = 'public'

Base = sqlalchemy.ext.declarative.declarative_base()

association_pubsys = \
    sqlalchemy.Table('publication_system',
                     Base.metadata,
                     sqlalchemy.Column('ase_id', String,
                                       sqlalchemy.ForeignKey(
                                           '{}.systems.unique_id'.format(SCHEMA)),
                                       # if PRODUCTION# else 'main.systems.pub_id'),
                                       primary_key=True),
                     sqlalchemy.Column('pub_id', String,
                                       sqlalchemy.ForeignKey(
                                           '{}.publication.pub_id'.format(SCHEMA)),
                                       # if PRODUCTION else 'main.publication.pub_id'),
                                       primary_key=True)
                     )


class Publication(Base):
    __tablename__ = 'publication'
    __table_args__ = ({'schema': SCHEMA})
    id = sqlalchemy.Column(Integer, primary_key=True)
    pub_id = sqlalchemy.Column(String, unique=True)
    title = sqlalchemy.Column(String, )
    authors = sqlalchemy.Column(JSONB, )
    journal = sqlalchemy.Column(String, )
    volume = sqlalchemy.Column(String, )
    number = sqlalchemy.Column(String, )
    pages = sqlalchemy.Column(String, )
    year = sqlalchemy.Column(Integer, )
    publisher = sqlalchemy.Column(String, )
    doi = sqlalchemy.Column(String, )
    tags = sqlalchemy.Column(JSONB, )
    pubtextsearch = sqlalchemy.Column(TSVECTOR, )
    stime = sqlalchemy.Column(Float, )
    reactions = sqlalchemy.orm.relationship(
        "Reaction", backref="publication", uselist=True)

    systems = sqlalchemy.orm.relationship("System",
                                          secondary=association_pubsys, uselist=True)

    @hybrid_property
    def _stime(self):
        if not self.stime:
            return None
        return (
            datetime.datetime(2000, 1, 1, 0, 0)
            + datetime.timedelta(
                seconds=int(
                    round(self.stime * ase.db.core.seconds['y'], 0))
            )
        ).strftime('%c')


class ReactionSystem(Base):
    __tablename__ = 'reaction_system'
    __table_args__ = ({'schema': SCHEMA})

    name = sqlalchemy.Column(String, )
    energy_correction = sqlalchemy.Column(Float, )
    ase_id = sqlalchemy.Column(String,
                               sqlalchemy.ForeignKey(
                                   '{}.systems.unique_id'.format(SCHEMA)),
                               primary_key=True)
    id = sqlalchemy.Column(Integer,
                           sqlalchemy.ForeignKey(
                               '{}.reaction.id'.format(SCHEMA)),
                           primary_key=True)


class Log(Base):
    __tablename__ = 'log'
    __table_args__ = ({'schema': SCHEMA})

    ase_id = sqlalchemy.Column(String,
                               sqlalchemy.ForeignKey(
                                   '{}.systems.unique_id'.format(SCHEMA)),
                               primary_key=True)
    logfile = sqlalchemy.Column(String, )
    logtype = sqlalchemy.Column(String, )

    @hybrid_property
    def _logtext(self):
        return bytes(self.logfile).decode('utf-8')


class Reaction(Base):
    __tablename__ = 'reaction'
    __table_args__ = ({'schema': SCHEMA})
    id = sqlalchemy.Column(Integer, primary_key=True)
    #rowid = sqlalchemy.sqlalchemy.Column(Integer)
    chemical_composition = sqlalchemy.Column(String, )
    surface_composition = sqlalchemy.Column(String, )
    facet = sqlalchemy.Column(String, )
    sites = sqlalchemy.Column(JSONB, )
    coverages = sqlalchemy.Column(JSONB, )
    reactants = sqlalchemy.Column(JSONB, )
    products = sqlalchemy.Column(JSONB, )
    reaction_energy = sqlalchemy.Column(Float, )
    activation_energy = sqlalchemy.Column(Float, )
    dft_code = sqlalchemy.Column(String, )
    dft_functional = sqlalchemy.Column(String, )
    username = sqlalchemy.Column(String, )
    pub_id = sqlalchemy.Column(String,  sqlalchemy.ForeignKey(
        '{}.publication.pub_id'.format(SCHEMA)))
    textsearch = sqlalchemy.Column(TSVECTOR, )

    reaction_systems = sqlalchemy.orm.relationship("ReactionSystem",
                                                   # primaryjoin="""ReactionSystem.id==Reaction.id""",
                                                   # uselist=False,
                                                   backref="reactions")

    systems = sqlalchemy.orm.relationship("System",
                                          primaryjoin="""ReactionSystem.id==Reaction.id""",
                                          secondaryjoin="ReactionSystem.ase_id==System.unique_id",
                                          secondary=sqlalchemy.inspect(
                                              ReactionSystem).tables[0],
                                          # lazy='joined',
                                          uselist=True,
                                          backref='reactions')

    @hybrid_property
    def _equation(self):
        equation = ''
        arrow = 0
        for column in (self.reactants, self.products):
            if arrow == 1:
                equation += ' -> '
            arrow += 1
            i = 0
            for key in sorted(column, key=len, reverse=True):
                prefactor = column[key]  # [1]
                #state = column[key][0]

                if 'gas' in key:
                    key = key.replace('gas', '(g)')
                if 'star' in key:
                    key = key.replace('star', '*')
                if not i == 0:
                    if prefactor > 0:
                        equation += ' + '
                    else:
                        equation += ' - '
                        prefactor *= -1
                if prefactor == 1:
                    prefactor = ''

                equation += str(prefactor) + key
                i += 1
        return equation


class Information(Base):
    __tablename__ = 'information'
    __table_args__ = ({'schema': SCHEMA})
    name = sqlalchemy.Column(String, primary_key=True)
    value = sqlalchemy.Column(String, )


class System(Base):
    __tablename__ = 'systems'
    __table_args__ = ({'schema': SCHEMA})
    id = sqlalchemy.Column(Integer, primary_key=True)
    #rowid = sqlalchemy.Column(Integer, )
    unique_id = sqlalchemy.Column(String, )
    ctime = sqlalchemy.Column(Float, )
    mtime = sqlalchemy.Column(Float, )
    username = sqlalchemy.Column(String)
    numbers = sqlalchemy.Column(ARRAY(Integer), )
    positions = sqlalchemy.Column(ARRAY(Float, dimensions=2))
    cell = sqlalchemy.Column(ARRAY(Float, dimensions=2))
    pbc = sqlalchemy.Column(Integer,)
    initial_magmoms = sqlalchemy.Column(ARRAY(Float),)
    initial_charges = sqlalchemy.Column(ARRAY(Float),)
    masses = sqlalchemy.Column(ARRAY(Float),)
    tags = sqlalchemy.Column(ARRAY(Float), )
    momenta = sqlalchemy.Column(ARRAY(String), )
    constraints = sqlalchemy.Column(String, )
    calculator = sqlalchemy.Column(String, )
    calculator_parameters = sqlalchemy.Column(String, )
    energy = sqlalchemy.Column(Float, )
    free_energy = sqlalchemy.Column(Float, )
    forces = sqlalchemy.Column(ARRAY(Float, dimensions=2))
    stress = sqlalchemy.Column(ARRAY(Float))
    dipole = sqlalchemy.Column(ARRAY(Float))
    magmoms = sqlalchemy.Column(ARRAY(Float))
    magmom = sqlalchemy.Column(Float, )
    charges = sqlalchemy.Column(ARRAY(Float))
    key_value_pairs = sqlalchemy.Column(JSONB, )
    data = sqlalchemy.Column(JSONB,)
    natoms = sqlalchemy.Column(Integer,)
    fmax = sqlalchemy.Column(Float, )
    smax = sqlalchemy.Column(Float, )
    volume = sqlalchemy.Column(Float, )
    mass = sqlalchemy.Column(Float, )
    charge = sqlalchemy.Column(Float, )

    keys = sqlalchemy.orm.relationship("Key", backref="systems", uselist=True)

    species = sqlalchemy.orm.relationship(
        "Species", backref="systems", uselist=True)
    text_keys = sqlalchemy.orm.relationship(
        "TextKeyValue", backref="systems", uselist=True)
    number_keys = sqlalchemy.orm.relationship(
        "NumberKeyValue", backref="systems", uselist=True)

    reaction_systems = sqlalchemy.orm.relationship(
        "ReactionSystem",
        backref="systems",
        uselist=True)

    log = sqlalchemy.orm.relationship(
        "Log",
        backref="systems",
        uselist=True)

    #reaction = sqlalchemy.orm.relationship("ReactionSystems", backref='systems', uselist=True)

    publication = sqlalchemy.orm.relationship("Publication",
                                              secondary=association_pubsys,
                                              uselist=True
                                              )

    ###################################
    # GENERAL ATOMS FORMATS
    ###################################

    def _toatoms(self, include_results=False):
        if not include_results:
            return ase.atoms.Atoms(
                self.numbers,
                self.positions,
                cell=self.cell,
                pbc=(self.pbc & np.array([1, 2, 4])).astype(bool),
            )
        if self.constraints:
            print(self.constraints)
            constraints = json.loads(self.constraints)
            print(constraints)
            if len(constraints[0]['kwargs']['indices']) > 0:
                constraints = [dict2constraint(d) for d in constraints]
        else:
            constraints = None
        atoms = ase.atoms.Atoms(self.numbers,
                                self.positions,
                                cell=self.cell,
                                pbc=(self.pbc & np.array(
                                    [1, 2, 4])).astype(bool),
                                magmoms=self.initial_magmoms,
                                charges=self.initial_charges,
                                tags=self.tags,
                                masses=self.masses,
                                momenta=self.momenta,
                                constraint=constraints)
        atoms.info = {}
        atoms.info['unique_id'] = self.unique_id
        atoms.info['key_value_pairs'] = self.key_value_pairs

        data = self.data
        if data:
            atoms.info['data'] = data

        if not self.calculator == "unknown":
            params = self.calculator_parameters
            atoms.calc = Calculator(self.calculator, **params)
            atoms.calc.name = self.calculator
        else:
            all_properties = ['energy', 'forces', 'stress', 'dipole',
                              'charges', 'magmom', 'magmoms', 'free_energy']
            results = {}
            for prop in all_properties:
                result = getattr(self, prop, None)
                if result is not None:
                    results[prop] = result
            if results:
                atoms.calc = SinglePointCalculator(atoms, **results)
                atoms.calc.name = getattr(self, 'calculator', 'unknown')
        return atoms

    @hybrid_property
    def _formula(self):
        return formula_metal(self.numbers)

    @hybrid_property
    def _cifdata(self):
        mem_file = StringIOStringIO()
        ase.io.write(mem_file, self._toatoms(), 'cif')
        return mem_file.getvalue()

    @hybrid_property
    def _trajdata(self):
        mem_file = StringIOStringIO()
        ase.io.write(mem_file, self._toatoms(include_results=True), 'json')
        return mem_file.getvalue()

    @hybrid_property
    def _pbc(self):
        return (self.pbc & np.array([1, 2, 4])).astype(bool).tolist()

    @hybrid_property
    def _ctime(self):
        return (
            datetime.datetime(2000, 1, 1, 0, 0)
            + datetime.timedelta(
                seconds=int(
                    round(self.ctime * ase.db.core.seconds['y'], 0))
            )
        ).strftime('%c')

    @hybrid_property
    def _mtime(self):
        return (
            datetime.datetime(2000, 1, 1, 0, 0)
            + datetime.timedelta(
                seconds=int(
                    round(self.mtime * ase.db.core.seconds['y'], 0))
            )
        ).strftime('%c')

    @hybrid_property
    def _adsorbate(self):
        return self.key_value_pairs.get('adsorbate', '')

    @hybrid_property
    def _reaction(self):
        return self.key_value_pairs.get('reaction', '')

    @hybrid_property
    def _username(self):
        return self.key_value_pairs.get('username', '')

    @hybrid_property
    def _substrate(self):
        return self.key_value_pairs.get('substrate', '')

    @hybrid_property
    def _facet(self):
        return self.key_value_pairs.get('facet', '').strip("()")

    @hybrid_property
    def _dft_code(self):
        return self.key_value_pairs.get('dft_code', '')

    @hybrid_property
    def _dft_functional(self):
        return self.key_value_pairs.get('dft_functional', '')


class Species(Base):
    __tablename__ = 'species'
    __table_args__ = ({'schema': SCHEMA})
    id = sqlalchemy.Column(Integer,
                           sqlalchemy.ForeignKey(
                               '{}.systems.id'.format(SCHEMA)),
                           primary_key=True)
    z = sqlalchemy.Column(Integer, primary_key=True,)
    n = sqlalchemy.Column(Integer, primary_key=True,)


class Key(Base):
    __tablename__ = 'keys'
    __table_args__ = ({'schema': SCHEMA})
    id = sqlalchemy.Column(Integer,
                           sqlalchemy.ForeignKey(
                               '{}.systems.id'.format(SCHEMA)),
                           primary_key=True)
    key = sqlalchemy.Column(String, primary_key=True)


class NumberKeyValue(Base):
    __tablename__ = 'number_key_values'
    __table_args__ = ({'schema': SCHEMA})
    id = sqlalchemy.Column(Integer,
                           sqlalchemy.ForeignKey(
                               '{}.systems.id'.format(SCHEMA)),
                           primary_key=True)
    key = sqlalchemy.Column(String, primary_key=True)
    value = sqlalchemy.Column(Float,)


class TextKeyValue(Base):
    __tablename__ = 'text_key_values'
    __table_args__ = ({'schema': SCHEMA})
    id = sqlalchemy.Column(Integer,
                           sqlalchemy.ForeignKey(
                               '{}.systems.id'.format(SCHEMA)),
                           primary_key=True)
    key = sqlalchemy.Column(String, primary_key=True)
    value = sqlalchemy.Column(String,)

class PublicationExp(Base):
    __tablename__ = 'publication'
    __table_args__ = ({'schema': 'experimental'})
    id = sqlalchemy.Column(Integer, primary_key=True)
    pub_id = sqlalchemy.Column(String, unique=True)
    title = sqlalchemy.Column(String, )
    authors = sqlalchemy.Column(JSONB, )
    journal = sqlalchemy.Column(String, )
    volume = sqlalchemy.Column(String, )
    number = sqlalchemy.Column(String, )
    pages = sqlalchemy.Column(String, )
    year = sqlalchemy.Column(Integer, )
    publisher = sqlalchemy.Column(String, )
    doi = sqlalchemy.Column(String, )
    tags = sqlalchemy.Column(JSONB, )
    stime = sqlalchemy.Column(Float, )

    @hybrid_property
    def _stime(self):
        if not self.stime:
            return None
        return (
            datetime.datetime(2000, 1, 1, 0, 0)
            + datetime.timedelta(
                seconds=int(
                    round(self.stime * ase.db.core.seconds['y'], 0))
            )
        ).strftime('%c')

class Material(Base):
    __tablename__ = 'material'
    __table_args__ = ({'schema': 'experimental'})
    mat_id = sqlalchemy.Column(Integer, primary_key=True)
    pub_id = sqlalchemy.Column(String,
                           sqlalchemy.ForeignKey(
                               'experimental.publication.pub_id'))
    composition = sqlalchemy.Column(String)
    arrangement = sqlalchemy.Column(String)
    icsd_ids = sqlalchemy.Column(ARRAY(Integer))
    icdd_ids = sqlalchemy.Column(ARRAY(Integer))
    space_group = sqlalchemy.Column(String)
    lattice_parameter = sqlalchemy.Column(String)
    morphology = sqlalchemy.Column(String)
    notes = sqlalchemy.Column(String)

class Sample(Base):
    __tablename__ = 'sample'
    __table_args__ = ({'schema': 'experimental'})
    sample_id = sqlalchemy.Column(Integer, primary_key=True)
    mat_id = sqlalchemy.Column(Integer,
                           sqlalchemy.ForeignKey(
                               'experimental.material.mat_id'))
    pub_id = sqlalchemy.Column(String,
                           sqlalchemy.ForeignKey(
                               'experimental.publication.pub_id'))
    data = sqlalchemy.Column(JSONB, )

class Xps(Base):
    __tablename__ = 'xps'
    __table_args__ = ({'schema': 'experimental'})
    mat_id = sqlalchemy.Column(Integer,
                       sqlalchemy.ForeignKey(
                           'experimental.material.mat_id'),
                                primary_key=True,)
    sample_id = sqlalchemy.Column(Integer,
                       sqlalchemy.ForeignKey(
                           'experimental.sample.sample_id'))
    xpstype = sqlalchemy.Column('type', String, )
    binding_energy = sqlalchemy.Column(ARRAY(Float))
    intensity = sqlalchemy.Column(ARRAY(Float))

class Xrd(Base):
    __tablename__ = 'xrd'
    __table_args__ = ({'schema': 'experimental'})
    mat_id = sqlalchemy.Column(Integer,
                       sqlalchemy.ForeignKey(
                           'experimental.material.mat_id'),
                               primary_key=True,)
    xrdtype = sqlalchemy.Column('type', String, )
    degree = sqlalchemy.Column(ARRAY(Float))
    intensity = sqlalchemy.Column(ARRAY(Float))

class Echemical(Base):
    __tablename__ = 'echemical'
    __table_args__ = ({'schema': 'experimental'})
    id = sqlalchemy.Column(Integer, primary_key=True)
    cvtype = sqlalchemy.Column('type', String, )
    total_time = sqlalchemy.Column(Float, )
    time = sqlalchemy.Column(ARRAY(Float))
    potential = sqlalchemy.Column(ARRAY(Float))
    current = sqlalchemy.Column(ARRAY(Float))
    sample_id = sqlalchemy.Column(Integer,
                       sqlalchemy.ForeignKey(
                           'experimental.sample.sample_id'))


def hybrid_prop_parameters(key):
    h_parameters = {'Formula': ['id', 'numbers'],
                    'Equation': ['id', 'reactants', 'products'],
                    'Cifdata': ['id', 'numbers', 'positions', 'cell', 'pbc'],
                    'Ctime': ['id', 'ctime'],
                    'Mtime': ['id', 'mtime'],
                    'Stime': ['id', 'stime'],
                    'Pbc': ['id', 'pbc'],
                    'Trajdata': ['all'],
                    'Logtext': ['logfile']}

    if key not in h_parameters:
        return ['id', 'key_value_pairs']

    return h_parameters[key]
