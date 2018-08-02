import copy
import json
import os
import os.path
import pprint
import zipfile
import time
import datetime
import math


# workaround to work on both Python 2 and Python 3
try:
    import io as StringIO
except ImportError:
    import StringIO

import numpy as np
import statistics

import flask

import mendeleev

import ase.atoms
import ase.io
import ase.build
import ase.io.formats
import ase.data

import catkit.build
import catkit.gen.adsorption
import catkit.gen.surface

import apps.utils.gas_phase_references
from apps.catlearn.atomistic import predict_catkit_demo


catKitDemo = flask.Blueprint('catKitDemo', __name__)

VERSION = 1

SITE_NAMES = [
    'gas',
    'top',
    'bridge',
    'hollow',
    '4fold',
]

VALID_OUT_FORMATS = [
    "abinit",
    "castep-cell",
    "cfg",
    "cif",
    "dlp4",
    "eon",
    "espresso-in",
    "extxyz",
    "findsym",
    "gen",
    "gromos",
    "json",
    "jsv",
    "nwchem",
    "proteindatabank",
    "py",
    "traj",
    "turbomole",
    "v-sim",
    "vasp",
    "xsf",
    "xyz"]


# safe settings for non-cubic large gas phase cell
GAS_PHASE_CELL = [15, 16, 17]

atomic_radii = {
    element.symbol:
    (element.atomic_radius
     or element.covalent_radius_cordero
     or element.covalent_radius_pyykko)
    for element in mendeleev.get_all_elements()}


class MockRequest(object):

    def __init__(self, args):
        self.args = json.dumps(args)

    def __repr__(self):
        return '[MockRequest] ' + pprint.pformat(self.args)


@catKitDemo.route('/generate_bulk_cif/', methods=['GET', 'POST'])
def generate_bulk_cif(request=None, return_atoms=False):
    request = flask.request if request is None else request
    if isinstance(request.args, str):
        request.args = json.loads(request.args)

    if isinstance(request.args.get('bulkParams', '{}'), str):
        bulk_params = json.loads(request.args.get('bulkParams', '{}'))
    else:
        bulk_params = request.args.get('bulkParams', {})

    cubic = bulk_params.get(
        'cubic', 'true').lower() == 'true'
    structure = bulk_params.get('structure', 'fcc')
    lattice_constant = float(bulk_params.get('lattice_constant', 4.0))

    elements = bulk_params.get('elements', ['Pt'])
    input_format = str(bulk_params.get('format', 'cif') or 'cif')

    if elements:
        lattice_constant = statistics.mean(
            atomic_radii[x] for x in elements) * (2 * math.sqrt(2) / 100.)

    for i in range(1, 5):
        try:
            atoms = ase.build.bulk(
                ''.join(
                    elements[
                        :i]),
                structure,
                a=lattice_constant,
                cubic=cubic)
            break
        except Exception as e:
            print(e)
            pass
    for i, atom in enumerate(atoms):
        atoms[i].symbol = elements[i % len(elements)]

    mem_file = StringIO.StringIO()
    #  Castep file writer needs name
    mem_file.name = 'Catalysis-Hub.Org Structure'
    ase.io.write(mem_file, atoms, 'cif')

    input_mem_file = StringIO.StringIO()
    #  Castep file writer needs name
    input_mem_file.name = 'Catalysis-Hub.Org Structure'
    ase.io.write(input_mem_file, atoms, input_format)

    if return_atoms:
        return atoms

    return flask.jsonify({
        'version': VERSION,
        'cifdata': mem_file.getvalue(),
        'lattice_constants': lattice_constant,
        'input': input_mem_file.getvalue(),
    })


@catKitDemo.route('/generate_slab_cif/', methods=['GET', 'POST'])
def generate_slab_cif(request=None, return_atoms=False):
    request = flask.request if request is None else request
    if hasattr(request, 'get_json'):
        request.values = dict((request.get_json() or {}),
                              **(request.values
                                  if type(request.values) is dict
                                  else request.values.to_dict()
                                 ))
    else:
        request.values = copy.deepcopy(request)

    if isinstance(request.values, str):
        request.values = json.loads(request.values)

    if isinstance(request.values.get('slabParams', '{}'), str):
        slab_params = json.loads(request.values.get('slabParams', '{}'))
    else:
        slab_params = request.values.get('slabParams', {})

    miller_x = int(slab_params.get('millerX', 1))
    miller_y = int(slab_params.get('millerY', 1))
    miller_z = int(slab_params.get('millerZ', 1))
    unit_cell_size = int(slab_params.get('unitCellSize', 2))
    layers = int(slab_params.get('layers', 4))
    fixed = int(slab_params.get('fixed', 2))
    axis = int(slab_params.get('axis', 2))
    vacuum = float(slab_params.get('vacuum', 10.))
    # stoichiometry = bool(slab_params.get('stoichiometry', False))
    termination = int(slab_params.get('termination', 0))
    input_format = str(slab_params.get('format', 'cif') or 'cif')
    all_terminations = slab_params.get('termination', 'false') == 'true'

    bulk_cif = str(request.values.get(
        'bulk_cif', (json.loads(generate_bulk_cif(request).data)['cifdata'])))

    mem_file = StringIO.StringIO()
    mem_file.write(bulk_cif)
    mem_file.seek(0)

    atoms = ase.io.read(mem_file, format='cif')

    Gen = catkit.gen.surface.SlabGenerator(
        bulk=atoms,
        miller_index=[miller_x,
                      miller_y,
                      miller_z
                      ],
        layers=layers,
        fixed=fixed,
        # fix_stoichiometry=stoichiometry,
        attach_graph=False,
    )
    terminations = Gen.get_unique_terminations()
    images = []
    mem_files = []
    input_mem_files = []
    n_terminations = len(terminations)

    for (iterm, term) in enumerate(terminations):
        if not all_terminations and 0 <= termination < n_terminations:
            if iterm != termination:
                continue
            terminations = [terminations[termination]]
        images.append(Gen.get_slab(
            iterm=iterm,
            size=(unit_cell_size, unit_cell_size)))
        images[-1].center(axis=axis, vacuum=vacuum)
        mem_files.append(StringIO.StringIO())
        #  Castep file writer needs name
        mem_files[-1].name = 'Catalysis-Hub.Org Structure'
        ase.io.write(mem_files[-1], images[-1], format='cif')
        mem_files[-1].seek(0)

        input_mem_files.append(StringIO.StringIO())
        #  Castep file writer needs name
        input_mem_files[-1].name = 'Catalysis-Hub.Org Structure'
        ase.io.write(input_mem_files[-1], images[-1], format=input_format)
        input_mem_files[-1].seek(0)

    if return_atoms:
        return images

    return flask.jsonify({
        'version': VERSION,
        'images': [mem_file.getvalue() for mem_file in mem_files],
        'input': [input_mem_file.getvalue() for
                  input_mem_file in input_mem_files],
        'n_terminations': n_terminations,
    })


@catKitDemo.route('/get_adsorption_sites', methods=['GET', 'POST'])
def get_adsorption_sites(request=None, return_atoms=False, place_holder=None,
                         make_predictions=False):
    """Returns a dictionary containing slab-adsorbate structures and metadata.
    """
    request = flask.request if request is None else request
    request.values = dict((request.get_json() or {}),
                          **request.values.to_dict(), )
    if isinstance(request.values, str):
        request.values = json.loads(request.values)

    if isinstance(request.values.get('slabParams', '{}'), str):
        slab_params = json.loads(request.values.get('slabParams', '{}'))
    else:
        slab_params = request.values.get('slabParams', {})

    miller_x = int(slab_params.get('millerX', 1))
    miller_y = int(slab_params.get('millerY', 1))
    miller_z = int(slab_params.get('millerZ', 1))
    unit_cell_size = int(slab_params.get('unitCellSize', 2))
    layers = int(slab_params.get('layers', 4))
    fixed = int(slab_params.get('fixed', 2))
    axis = int(slab_params.get('axis', 2))
    vacuum = float(slab_params.get('vacuum', 10.))
    stoichiometry = bool(slab_params.get('stoichiometry', False))
    input_format = str(slab_params.get('format', 'cif') or 'cif')

    bulk_cif = str(request.values.get(
        'bulk_cif', (json.loads(generate_bulk_cif(request).data)['cifdata'])))
    # cif_images = json.loads(generate_slab_cif(request).data)['images']

    if isinstance(request.values.get('adsorbateParams', '{}'), str):
        adsorbate_params = json.loads(
            request.values.get('adsorbateParams', '{}'))
    else:
        adsorbate_params = request.values.get('adsorbateParams', {})

    if place_holder is None:
        place_holder = str(adsorbate_params.get('placeHolder', 'empty'))

    species = str(adsorbate_params.get('adsorbate', 'O'))
    site_type = str(adsorbate_params.get('siteType', 'all'))
    make_predictions = bool(adsorbate_params.get('callCatLearn', False))

    # create bulk atoms
    mem_file = StringIO.StringIO()
    mem_file.write(bulk_cif)
    mem_file.seek(0)

    bulk_atoms = ase.io.read(mem_file, format='cif')
    with StringIO.StringIO() as f:
        #  Castep file writer needs name
        f.name = 'Catalysis-Hub.Org Structure'
        ase.io.write(f, bulk_atoms, format='py')
        _batoms = '='.join(f.getvalue().split('=')[1:])

    gen = catkit.gen.surface.SlabGenerator(
        bulk=bulk_atoms,
        miller_index=[miller_x, miller_y, miller_z],
        layers=layers,
        fixed=fixed,
        vacuum=vacuum,
        # fix_stoichiometry=stoichiometry,
    )
    slab = gen.get_slab(size=(unit_cell_size, unit_cell_size))
    sites = gen.adsorption_sites(
            slab,
            symmetry_reduced=True)
    sites = [list(sites[0]), list(sites[1])]

    builder = catkit.gen.adsorption.Builder(slab)
    adsorbate = catkit.build.molecule(species)[0]
    adsorbate.set_tags([-1])
    atoms_objects = builder.add_adsorbate(adsorbate, index=-1)

    in_mem_files = []
    sites_list = []
    cif_images = []
    input_images = []
    equations = []
    site_names = []
    site_types = []
    error_message = ''
    old_n_bonds = ''
    site_counter = 0
    for atoms_i, atoms in enumerate(atoms_objects):

        # Set adsorbate metadata for CatLearn.
        atoms.info['key_value_pairs'] = {'species': species}

        if site_type != sites[1][atoms_i] and site_type != 'all':
            continue

        reference_molecules = {}

        # Structures for DFT calculations.
        with StringIO.StringIO() as f:
            #  Castep file writer needs name
            f.name = 'Catalysis-Hub.Org Structure'
            ase.io.write(f, atoms, format=input_format)
            input_images.append(f.getvalue())

        symbols = apps.utils.gas_phase_references.molecules2symbols(
            [species])
        references = \
            apps.utils.gas_phase_references.construct_reference_system(
                    symbols)
        stoichiometry = \
            apps.utils.gas_phase_references.get_atomic_stoichiometry(
                references)
        stoichiometry_factors = \
            apps.utils.gas_phase_references.get_stoichiometry_factors(
                [species], references)

        molecules = []
        for molecule_name in [x[1] for x in references]:
            molecule = ase.build.molecule(molecule_name)
            molecule.cell = np.diag(GAS_PHASE_CELL)

            with StringIO.StringIO() as f:
                #  Castep file writer needs name
                f.name = 'Catalysis-Hub.Org Structure'
                ase.io.write(f, molecule, format=input_format)
                reference_molecules[molecule_name] = f.getvalue()

        reactants = []
        gas_phase_molecules = set()
        for molecule, factor in stoichiometry_factors[
                species].items():
            reactants.append(
                '{factor}{molecule}gas'.format(**locals()))
            gas_phase_molecules.add(molecule)

        reactants = '_'.join(reactants)
        n_bonds = sites[1][atoms_i]
        _site_name = SITE_NAMES[n_bonds]

        if n_bonds != old_n_bonds:
            site_counter += 1
        old_n_bonds = n_bonds
        site_types.append(n_bonds)
        site_names.append(n_bonds)
        site_name = '{_site_name}{site_counter}'.format(**locals())
        equation = 'star@{site_name}_{reactants}__' + \
            '{adsorbate}star@{site_name}'.format(**locals())
        equations.append(equation)

        # Add placeholders.
        atoms = copy.deepcopy(atoms)
        if place_holder != 'empty':
            for i, (site, n_bonds) in enumerate(zip(*sites)):
                if atoms_i != i:
                    atoms += ase.atom.Atom(
                        place_holder,
                        sites[0][i] + [0., 0., 1.5])
        # Structures for the viewer on catalysishub.
        if not return_atoms:
            with StringIO.StringIO() as f:
                #  Castep file writer needs name
                f.name = 'Catalysis-Hub.Org Structure'
                ase.io.write(f, atoms, format='cif')
                cif_images.append(f.getvalue())

    if make_predictions:
        # Gaussian process regression model predictions on adsorption energies.
        predictions = predict_catkit_demo(atoms_objects)
    else:
        predictions = {}

    alt_labels = [{}]
    if return_atoms:
        dictionary = {
            'version': VERSION,
            'data': (sites_list),
            'images': atoms_objects,
            'equations': equations,
            'molecules': reference_molecules,
            'site_types': site_types,
            'site_names': site_names,
            'altLabels': alt_labels,
            'error': error_message}
        dictionary.update(predictions)
        return dictionary
    else:
        dictionary = {
            'version': VERSION,
            'data': (sites_list),
            'cifImages': cif_images,  # Used by the viewer.
            'inputImages': input_images,
            'equations': equations,
            'molecules': reference_molecules,
            'site_types': site_types,
            'site_names': site_names,
            'altLabels': alt_labels,
            'error': error_message}
        dictionary.update(predictions)
        return flask.jsonify(dictionary)


@catKitDemo.route('/generate_dft_input', methods=['GET', 'POST'])
def generate_dft_input(request=None, return_data=False):
    request = flask.request if request is None else request
    if isinstance(request.args, str):
        request.args = json.loads(request.args)

    # Generate Zip File
    ####################
    timestr = time.strftime(
        "%Y%m%d_%H%M%S", datetime.datetime.now().timetuple())
    calcstr = "calculations_{timestr}".format(**locals())
    zip_mem_file = StringIO.BytesIO()
    zf = zipfile.ZipFile(zip_mem_file, 'w')
    zf.writestr(
        '{calcstr}/publication.txt'.format(**locals()),
        '{"volume": "",\n'
        '"publisher": "",\n'
        '"doi": "",\n'
        '"title": "",\n'
        '"journal": "",\n'
        '"authors": [],\n'
        '"year": "",\n'
        '"number": "",\n'
        '"pages": ""}\n')
#

    data = []

    # Unpack request
    ####################
    calculations = json.loads(request.args.get('calculations', '[]'))
    input_json = json.dumps(calculations, indent=4, sort_keys=True)

    zf.writestr('{calcstr}/input.json'.format(**locals()),
                input_json,
                )
    adsorbate_names = []
    gas_phase_molecules = set()
    for i, calculation in enumerate(calculations):
        adsorbate_params = (calculation.get('adsorbateParams', {}))
        adsorbate_names.append(adsorbate_params['adsorbate'])
    symbols = apps.utils.gas_phase_references.molecules2symbols(
        adsorbate_names)
    references = apps.utils.gas_phase_references.construct_reference_system(
        symbols)
    stoichiometry = apps.utils.gas_phase_references.get_atomic_stoichiometry(
        references)
    stoichiometry_factors = \
        apps.utils.gas_phase_references.get_stoichiometry_factors(
            adsorbate_names, references)

    for i, calculation in enumerate(calculations):
        bulk_params = (calculation.get('bulkParams', {}))
        slab_params = (calculation.get('slabParams', {}))
        adsorbate_params = (calculation.get('adsorbateParams', {}))
        site_occupation = (calculation.get('siteOccupations', {}))
        dft_params = (calculation.get('dftParams', {}))
        calculation_data = {}

        # Unpack a little further ...
        miller_x = slab_params.get('millerX', 'N')
        miller_y = slab_params.get('millerY', 'N')
        miller_z = slab_params.get('millerZ', 'N')
        unit_cell_size = int(slab_params.get('unitCellSize', 2))
        facet = '{miller_x}_{miller_y}_{miller_z}'.format(**locals())

        composition = ''.join(bulk_params.get('elements', []))
        structure = bulk_params.get('structure', '')

        # Use Spacegroup-Wyckoff based synonym
        structure = bulk_params.get('wyckoff', {}).get(
            'synonyms', [structure])[0]

        adsorbate_names.append(adsorbate_params['adsorbate'])

        # Fix filetype and extension
        FORMAT2EXTENSION = {v: k for k,
                            v in ase.io.formats.extension2format.items()}
        CALC_FORMAT = FORMAT2EXTENSION.get(
            dft_params['calculator'], 'espresso-in')
        SUFFIX = ase.io.formats.extension2format.get(
            CALC_FORMAT, 'espresso-in')

        mock_request = MockRequest(calculation)
        # Here be Dragons
        ####################
        # print("Calculation {i}".format(**locals()))

        # 0. Construct ASE DFT Calculator
        #######################

        # 3. Add adsorbates
        #################################
        adsorbates = get_adsorption_sites(
            mock_request, return_atoms=True, place_holder='empty')
        images = adsorbates['images']
        site_names = adsorbates['site_names']
        adsorbates_strings = []
        site_counter = {}
        for image_i, image in enumerate(images):
            # Generate Adsorbates String
            adsorbate = str(adsorbate_params.get('adsorbate', 'empty'))
            reactants = []
            for molecule, factor in stoichiometry_factors[adsorbate].items():
                reactants.append('{factor}{molecule}gas'.format(**locals()))
                gas_phase_molecules.add(molecule)

            reactants = '_'.join(reactants)
            site_name = site_names[image_i]
            equation = 'star@{site_name}_{reactants}__' + \
                '{adsorbate}star@{site_name}'.format(**locals())
            site_counter[site_name] = site_counter.get(site_name, 0) + 1
            count = site_counter[site_name]
            adsorbates = '{adsorbate}star{site_name}.{count}'.format(
                **locals())

            adsorbates_strings.append(adsorbates)
            slab_path = '{calcstr}/{dft_params[calculator]}/' + \
                '{dft_params[functional]}/{composition}__{structure}/' + \
                '{facet}/{equation}'.format(**locals())

            if return_data:
                calculation_data.setdefault(
                    dft_params['calculator'],
                    {}) .setdefault(
                    dft_params['functional'],
                    {}) .setdefault(
                    '{composition}__{structure}'.format(
                        **locals()),
                    {}) .setdefault(
                    facet,
                    {}) .setdefault(
                        equation,
                    image)
            else:
                with StringIO.StringIO() as mem_file:
                    #  Castep file writer needs name
                    mem_file.name = 'Catalysis-Hub.Org Structure'
                    ase.io.write(mem_file, image, format=SUFFIX)
                    zf.writestr(
                        '{slab_path}/{adsorbates}.{SUFFIX}'.format(**locals()),
                        mem_file.getvalue(),
                    )

            # 2. Create empty surface slab
            #################################
            slab_images = generate_slab_cif(
                mock_request, return_atoms=True) * len(site_names)
            for slab_image_i, slab_image in enumerate(slab_images):
                adsorbate = str(adsorbate_params.get('adsorbate', 'empty'))
                site_name = site_names[slab_image_i]

                reactants = []
                for molecule, factor in stoichiometry_factors[
                        adsorbate].items():

                    reactants.append(
                        '{factor}{molecule}gas'.format(**locals()))
                reactants = '_'.join(reactants)
                site_name = site_names[image_i]
                equation = 'star{site_name}_{reactants}__' + \
                    '{adsorbate}star{site_name}'.format(**locals())

                adsorbates = '{adsorbate}star{site_name}'.format(**locals())
                slab_path = '{calcstr}/{dft_params[calculator]}/' + \
                    '{dft_params[functional]}/{composition}__{structure}/' + \
                    '{facet}/star.{SUFFIX}'.format(**locals())

                if slab_path not in zf.namelist():
                    if return_data:
                        calculation_data.setdefault(
                            dft_params['calculator'],
                            {}) .setdefault(
                            dft_params['functional'],
                            {}) .setdefault(
                            '{composition}__{structure}'.format(
                                **locals()),
                            {}) .setdefault(
                            facet,
                            {}) .setdefault(
                            'star',
                            slab_image)
                    else:
                        with StringIO.StringIO() as mem_file:
                            #  Castep file writer needs name
                            mem_file.name = 'Catalysis-Hub.Org Structure'
                            ase.io.write(mem_file, slab_image, format=SUFFIX)
                            zf.writestr(
                                slab_path.format(**locals()),
                                mem_file.getvalue(),
                            )

            # 1. Create Bulk Input
            #######################
            bulk_atoms = generate_bulk_cif(mock_request, return_atoms=True)

            reactants = []
            for molecule, factor in stoichiometry_factors[adsorbate].items():

                reactants.append('{factor}{molecule}gas'.format(**locals()))
            reactants = '_'.join(reactants)
            site_name = site_names[image_i]
            equation = 'star{site_name}_{reactants}__' + \
                '{adsorbate}star{site_name}'.format(**locals())

            bulk_path = '{calcstr}/{dft_params[calculator]}/' + \
                '{dft_params[functional]}/{composition}__{structure}/' + \
                'bulk.{SUFFIX}'.format(**locals())

            if bulk_path not in zf.namelist():
                if return_data:
                    calculation_data.setdefault(
                        dft_params['calculator'],
                        {}) .setdefault(
                        dft_params['functional'],
                        {}) .setdefault(
                        '{composition}__{structure}'.format(
                            **locals()),
                        {}) .setdefault(
                        'bulk',
                        bulk_atoms)
                else:
                    with StringIO.StringIO() as mem_file:
                        #  Castep file writer needs name
                        mem_file.name = 'Catalysis-Hub.Org Structure'
                        ase.io.write(mem_file, bulk_atoms, format=SUFFIX)
                        zf.writestr(
                            bulk_path,
                            mem_file.getvalue(),
                        )

        # 4. Add gas phase calculations
        #################################

        # TODO
        for molecule_name in gas_phase_molecules:
            molecule = ase.build.molecule(molecule_name)
            molecule.cell = np.diag(GAS_PHASE_CELL)
            molecule_path = '{calcstr}/{dft_params[calculator]}/' + \
                '{dft_params[functional]}/gas/' + \
                '{molecule_name}_gas.{SUFFIX}'.format(**locals())

            if molecule_path not in zf.namelist():
                if return_data:
                    calculation_data.setdefault(
                        dft_params['calculator'],
                        {}) .setdefault(
                        dft_params['functional'],
                        {}) .setdefault(
                        'gas',
                        {}) .setdefault(
                        '{molecule_name}_gas'.format(
                            **locals()),
                        molecule)
                else:
                    with StringIO.StringIO() as mem_file:
                        #  Castep file writer needs name
                        mem_file.name = 'Catalysis-Hub.Org Structure'
                        ase.io.write(mem_file, molecule, format=SUFFIX)
                        zf.writestr(molecule_path, mem_file.getvalue())

        data.append(calculation_data)

    if return_data:
        return data

    zf.close()
    zip_mem_file.seek(0)
    return flask.send_file(
        zip_mem_file,
        attachment_filename="{calcstr}.zip".format(**locals()),
        as_attachment=True,
        mimetype='application/x-zip-compressed',
    )


@catKitDemo.route('/convert_atoms/', methods=['GET', 'POST'])
def convert_atoms(request=None):
    import ase.io
    import ase.io.formats
    request = flask.request if request is None else request

    cif = request.args.get('cif',
                           request.get_json().get('params', {}).get('cif', '')
                           )
    out_format = request.args.get(
        'format', request.get_json().get(
            'params', {}).get(
            'format', ''))

    if not out_format:
        out_format = 'cif'
    if out_format not in VALID_OUT_FORMATS:
        return {
            "error": "outFormat {outformat} is invalid." +
            " Should be on of {VALID_OUT_FORMATS}".format(**locals())}

    with StringIO.StringIO() as in_file:
        in_file.write(cif)
        in_file.seek(0)
        atoms = ase.io.read(
            filename=in_file,
            index=None,
            format='cif',
        )

    composition = atoms.get_chemical_formula(mode='metal')

    with StringIO.StringIO() as out_file:
        #  Castep file writer needs name
        out_file.name = 'CatApp Browser Export'
        ase.io.write(out_file, atoms, out_format)
        out_content = out_file.getvalue()

    format2extension = {value: key for key,
                        value in ase.io.formats.extension2format.items()}

    extension = format2extension.get(out_format, out_format)

    return flask.jsonify({
        'version': VERSION,
        'image': str(out_content),
        'input_filetype': 'cif',
        'output_filetype': out_format,
        'filename': 'structure_{composition}.{extension}'.format(**locals()),
        'filename_trunk': 'structure_{composition}'.format(**locals()),
        'extension': extension,
    })


@catKitDemo.route('/upload_dataset/', methods=['GET', 'POST'])
def upload_dataset(request=None):
    request = flask.request if request is None else request
    filename = request.files['file'].filename
    suffix = os.path.splitext(filename)[1]
    if suffix == '.zip':
        message = ("You uploaded a zip file")
        suffix = 'ZIP'
    elif suffix in ['.tgz', '.tar.gz']:
        message = ("You uploaded a tar file.")
        suffix = 'TGZ'
    else:
        message = 'Could not detect filetype.'
        suffix = None

    with StringIO.BytesIO() as in_bfile:
        request.files['file'].save(in_bfile)

    return flask.jsonify({
        'version': VERSION,
        'message': message,
    })
