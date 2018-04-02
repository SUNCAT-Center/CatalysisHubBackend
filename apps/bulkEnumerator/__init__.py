import copy
import json
import os
import os.path
import pprint
import zipfile
import time
import datetime
import random
import re

# workaround to work on both Python 2 and Python 3
try:
    import io as StringIO
except:
    import StringIO

import numpy as np

import flask

import ase.atoms
import ase.io
import ase.build
import ase.io.formats


try:
    import bulk_enumerator as be
except:
    print("Warning: could not import bulk_enumerator, check installation.")
    be = None
import apps.utils

bulk_enumerator = flask.Blueprint('bulk_enumerator', __name__)


def stripb(string):
    return re.sub("^b'([^']*)'", r'\1', string)

def mstripb(liste):
    return list(map(stripb, liste))

@bulk_enumerator.route('/get_wyckoff_list', methods=['GET', 'POST'])
def get_wyckoff_list(request=None):
    """
    Return a list of possible wyckoff position belonging to a certain spacegroup.

    Args:

        spacegroup (int, optional) Spacegroup between 1-230. Defaults to 1.
        tolerance (float, optional) Tolerance. Defaults to 1e-5.

    """
    # housekeeping for both incoming and internal requests
    request = flask.request if request is None else request
    if type(request.args) is str:
        request.args = json.loads(request.args)

    # unpack arguments
    spacegroup = int(request.args.get('spacegroup', 1))
    tolerance = float(request.args.get('tolerance', 1e-3))

    # build results
    bulk = be.bulk.BULK()
    bulk.set_spacegroup(spacegroup)
    wyckoff_list = bulk.get_wyckoff_list()
    wyckoff_list.sort(
        key=lambda x: x['symbol'],
    )

    wyckoff_list = list(map(
        lambda x: dict(x, **{
            'symbol': stripb(x['symbol']),
            'species': '',
            'value': '0.5',
        }),
        wyckoff_list,
    ))

    # reclaim memory
    bulk.delete()

    return flask.jsonify({
        'wyckoff_list': wyckoff_list,
    })


@bulk_enumerator.route('/get_structure', methods=['GET', 'POST'])
def get_structure(request=None):
    """
    Construct structure from wyckoff positions, species, and other parameters

    Args:
        wyckoffPositions ([str]): List of Wyckoff positions (length one strings).
        wyckoffSpecies ([str]): Corresponding list of elements.


    """
    # housekeeping for both incoming and internal requests
    request = flask.request if request is None else request
    if type(request.args) is str:
        request.args = json.loads(request.args)

    # unpack arguments
    spacegroup = int(request.args.get('spacegroup', 1))
    tolerance = float(request.args.get('tolerance', 1e-5))
    if type(request.args.get('wyckoffPositions', '[]')) is str:
        wyckoff_positions = (json.loads(
            request.args.get('wyckoffPositions[]', '[]')))
    else:
        wyckoff_positions = (request.args.get('wyckoffPositions[]', []))

    if type(request.args.get('wyckoffSpecies', '[]')) is str:
        wyckoff_species = (json.loads(
            request.args.get('wyckoffSpecies[]', '[]')))
    else:
        wyckoff_species = (request.args.get('wyckoffSpecies[]', []))

    if type(request.args.get('wyckoffParams', '{}')) is str:
        wyckoff_params = json.loads(request.args.get('wyckoffParams', '{}'))
    else:
        wyckoff_params = request.args.get('wyckoffParams', {})

    if type(request.args.get('cellParams', '{}')) is str:
        cell_params = json.loads(request.args.get('cellParams', '{}'))
    else:
        cell_params = request.args.get('cellParams', {})

    # input sanity checks
    assert len(wyckoff_positions) == len(wyckoff_species)
    #assert len(wyckoff_positions) == len(wyckoff_params)

    # build results
    bulk = be.bulk.BULK()
    bulk.set_spacegroup(spacegroup)
    bulk.set_wyckoff(wyckoff_positions)
    bulk.set_species(wyckoff_species)

    # fill out default params
    # and overwrite them with cell_params, where present
    required_parameters = map(lambda x: x.decode(
        'utf-8'), map(eval, bulk.get_parameters()))

    default_cell_params = {
        'a': 3.,
        'b/a': 1.,
        'c/a': 1.,
        'alpha': 90,
        'beta': 90,
        'gamma': 90,
        'x': .5,
        'y': .5,
        'z': .5,
    }
    # default_cell_params.update(cell_params)
    #cell_params = default_cell_params
    for required_parameter in required_parameters:
        cell_params[required_parameter] = round(float(
        cell_params.get(required_parameter,
          default_cell_params.get(required_parameter,
                                  .1 + random.random() * .8))), 5)
        # i.e. a random number in [.1, .9]

    cell_params = {key: float(value) for key, value in cell_params.items()}
    bulk.set_parameter_values(*list(zip(*list(cell_params.items()))))

    std_poscar = bulk.get_std_poscar()
    primitive_poscar = bulk.get_primitive_poscar()

    synonyms =  mstripb(bulk.get_synonyms())

    # reclaim memory
    bulk.delete()

    return flask.jsonify({
        'std_cif': apps.utils.ase_convert(std_poscar, 'vasp', 'cif'),
        'primitive_cif': apps.utils.ase_convert(primitive_poscar, 'vasp', 'cif'),
        'cell_params': cell_params,
        'synonyms': synonyms,
    })


@bulk_enumerator.route('/get_wyckoff_from_structure', methods=['GET', 'POST'])
def get_wyckoff_from_structure(request=None):
    import ase.io
    import ase.io.formats
    request = flask.request if request is None else request
    if hasattr(request, 'files'):
        filename = request.files['file'].filename
        with StringIO.BytesIO() as in_bfile:
            request.files['file'].save(in_bfile)
            with StringIO.StringIO() as in_file:
                content = in_file.getvalue()
                in_bfile.seek(0)
                try:
                    in_file.write(in_bfile.getvalue().decode('UTF-8'))
                except Exception as error:
                    in_file = in_bfile
                in_file.seek(0)

                instring = (in_file.getvalue())
        filetype = ase.io.formats.filetype(filename, read=False)

    elif 'cif' in request.args:
        instring = request.args('cif')
        filetype = 'cif'


    atoms = apps.utils.ase_convert(instring, informat=filetype, atoms_out=True, )
    poscar = apps.utils.ase_convert(instring, informat=filetype, outformat='vasp')
    cif = apps.utils.ase_convert(instring, informat=filetype, outformat='cif')

    bulk = be.bulk.BULK()
    bulk.set_structure_from_file(poscar)

    # Evaluate Structure
    #####################
    t0 = time.time()
    wyckoff_list = bulk.get_wyckoff_list()
    parameter_values = bulk.get_parameter_values()
    spacegroup = bulk.get_spacegroup()
    wyckoff = bulk.get_wyckoff()
    species = bulk.get_species()
    synonyms = bulk.get_synonyms()
    species_permutations = bulk.get_species_permutations()

    poscar = bulk.get_std_poscar().decode('utf-8')
    cif = str(apps.utils.ase_convert(poscar, informat='vasp', outformat='cif'))

    ts = time.time() - t0

    bulk.delete()

    return flask.jsonify({
        'poscar': poscar,
        'cif': cif,
        'wyckoff_list': wyckoff_list,
        'runtime': ts,
        'parameter_values': parameter_values,
        'spacegroup': spacegroup,
        'wyckoff': wyckoff,
        'species': species,
        'synonyms': synonyms,
        'species_permutations': species_permutations,
    })


@bulk_enumerator.route('/get_wyckoff_from_cif', methods=['GET', 'POST'])
def get_wyckoff_from_cif(request=None):
    """
    Function clone of get_wyckoff_from_structure, except working w/ string input
    instead of file upload.
    """

    import ase.io
    import ase.io.formats
    request = flask.request if request is None else request

    instring = request.args.get('cif')
    filetype = 'cif'

    atoms = apps.utils.ase_convert(instring, informat=filetype, atoms_out=True, )
    poscar = apps.utils.ase_convert(instring, informat=filetype, outformat='vasp')
    cif = apps.utils.ase_convert(instring, informat=filetype, outformat='cif')

    bulk = be.bulk.BULK()
    bulk.set_structure_from_file(poscar)

    # Evaluate Structure
    #####################
    t0 = time.time()
    wyckoff_list = bulk.get_wyckoff_list()
    wyckoff_list = list(map(
        lambda x: dict(x, **{
            'symbol': stripb(x['symbol']),
        }),
        wyckoff_list,
    ))

    parameter_values = bulk.get_parameter_values()
    parameter_values = list(map(
        lambda x: dict(x, **{
            'name': stripb(x['name']),
            'value': x['value'],
        }),
        parameter_values,
    ))
    spacegroup = bulk.get_spacegroup()
    wyckoff = bulk.get_wyckoff()
    species = bulk.get_species()
    synonyms = bulk.get_synonyms()
    species_permutations = bulk.get_species_permutations()

    poscar = bulk.get_std_poscar().decode('utf-8')
    cif = str(apps.utils.ase_convert(poscar, informat='vasp', outformat='cif'))

    ts = time.time() - t0

    bulk.delete()

    return flask.jsonify({
        'poscar': poscar,
        'cif': cif,
        'wyckoff_list': wyckoff_list,
        'runtime': ts,
        'parameter_values': parameter_values,
        'spacegroup': spacegroup,
        'wyckoff': mstripb(wyckoff),
        'species': mstripb(species),
        'synonyms': mstripb(synonyms),
        'species_permutations': mstripb(species_permutations),
    })
