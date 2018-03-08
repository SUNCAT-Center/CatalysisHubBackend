import copy
import json
import os
import os.path
import pprint
import zipfile
import time
import datetime


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


import apps.utils.gas_phase_references

import catkit
import catkit.surface

catKitDemo = flask.Blueprint('catKitDemo', __name__)

VALID_OUT_FORMATS = ["abinit", "castep-cell", "cfg", "cif", "dlp4", "eon", "espresso-in", "extxyz", "findsym",
                     "gen", "gromos", "json", "jsv", "nwchem", "proteindatabank", "py", "turbomole", "v-sim", "vasp", "xsf", "xyz"]


# safe settings for non-cubic large gas phase cell
GAS_PHASE_CELL = [15, 16, 17]


class MockRequest(object):

    def __init__(self, args):
        self.args = json.dumps(args)

    def __repr__(self):
        return '[MockRequest] ' + pprint.pformat(self.args)


@catKitDemo.route('/generate_bulk_cif/', methods=['GET', 'POST'])
def generate_bulk_cif(request=None, return_atoms=False):
    request = flask.request if request is None else request
    if type(request.args) is str:
        request.args = json.loads(request.args)

    if type(request.args.get('bulkParams', '{}')) is str:
        bulk_params = json.loads(request.args.get('bulkParams', '{}'))
    else:
        bulk_params = request.args.get('bulkParams', {})

    cubic = bulk_params.get(
        'cubic', 'true').lower() == 'true'
    structure = bulk_params.get('structure', 'fcc')
    lattice_constant = float(bulk_params.get('lattice_constant', 4.0))

    elements = bulk_params.get('elements')

    for i in range(1, 5):

        try:
            atoms = ase.build.bulk(
                ''.join(elements[:i]), structure, a=lattice_constant, cubic=cubic)
            break
        except Exception as e:
            print(e)
            pass
    for i, atom in enumerate(atoms):
        atoms[i].symbol = elements[i % len(elements)]

    mem_file = StringIO.StringIO()
    ase.io.write(mem_file, atoms, 'cif')
    if return_atoms:
        return atoms

    return flask.jsonify({
        'cifdata': mem_file.getvalue(),
    })


@catKitDemo.route('/generate_slab_cif/', methods=['GET', 'POST'])
def generate_slab_cif(request=None, return_atoms=False):
    request = flask.request if request is None else request
    if type(request.args) is str:
        request.args = json.loads(request.args)

    if type(request.args.get('slabParams', '{}')) is str:
        slab_params = json.loads(request.args.get('slabParams', '{}'))
    else:
        slab_params = request.args.get('slabParams', {})

    miller_x = int(slab_params.get('millerX', 1))
    miller_y = int(slab_params.get('millerY', 1))
    miller_z = int(slab_params.get('millerZ', 1))
    layers = int(slab_params.get('layers', 4))
    axis = int(slab_params.get('axis', 2))
    vacuum = float(slab_params.get('vacuum', 10.))
    termination = int(slab_params.get('termination', 0))
    all_terminations = slab_params.get('termination', 'false') == 'true'

    bulk_cif = str(request.args.get(
        'bulk_cif', (json.loads(generate_bulk_cif(request).data)['cifdata'])))

    mem_file = StringIO.StringIO()
    mem_file.write(bulk_cif)
    mem_file.seek(0)

    atoms = ase.io.read(mem_file, format='cif')

    Gen = catkit.surface.SlabGenerator(
        bulk=atoms,
        miller_index=[miller_x,
                      miller_y,
                      miller_z
                      ],
        layers=layers,
    )
    terminations = Gen.get_unique_terminations()
    images = []
    mem_files = []
    n_terminations = len(terminations)

    for (iterm, term) in enumerate(terminations):
        if not all_terminations and 0 <= termination < n_terminations:
            if iterm != termination:
                continue
            terminations = [terminations[termination]]
        images.append(Gen.get_slab(iterm=iterm))
        images[-1].center(axis=axis, vacuum=vacuum)
        mem_files.append(StringIO.StringIO())
        ase.io.write(mem_files[-1], images[-1], format='cif')
        mem_files[-1].seek(0)

    if return_atoms:
        return images

    return flask.jsonify({
        'images': [mem_file.getvalue() for mem_file in mem_files],
        'n_terminations': n_terminations,
    })


@catKitDemo.route('/get_adsorption_sites', methods=['GET', 'POST'])
def get_adsorption_sites(request=None, return_atoms=False, place_holder=None):
    request = flask.request if request is None else request
    if type(request.args) is str:
        request.args = json.loads(request.args)

    if type(request.args.get('slabParams', '{}')) is str:
        slab_params = json.loads(request.args.get('slabParams', '{}'))
    else:
        slab_params = request.args.get('slabParams', {})

    miller_x = int(slab_params.get('millerX', 1))
    miller_y = int(slab_params.get('millerY', 1))
    miller_z = int(slab_params.get('millerZ', 1))
    layers = int(slab_params.get('layers', 4))
    axis = int(slab_params.get('axis', 2))
    vacuum = float(slab_params.get('vacuum', 10.))

    bulk_cif = str(request.args.get(
        'bulk_cif', (json.loads(generate_bulk_cif(request).data)['cifdata'])))
    cif_images = json.loads(generate_slab_cif(request).data)['images']

    if type(request.args.get('adsorbateParams', '{}')) is str:
        adsorbate_params = json.loads(
            request.args.get('adsorbateParams', '{}'))
    else:
        adsorbate_params = request.args.get('adsorbateParams', {})

    if place_holder is None:
        place_holder = str(adsorbate_params.get('placeHolder', 'F'))

    adsorbate = str(adsorbate_params.get('adsorbate', 'O'))

    site_type = str(adsorbate_params.get('siteType', 'all'))

    # create bulk atoms
    mem_file = StringIO.StringIO()
    mem_file.write(bulk_cif)
    mem_file.seek(0)

    bulk_atoms = ase.io.read(mem_file, format='cif')
    with StringIO.StringIO() as f:
        ase.io.write(f, bulk_atoms, format='py')
        _batoms = '='.join(f.getvalue().split('=')[1:])

    gen = catkit.surface.SlabGenerator(
        bulk=bulk_atoms,
        miller_index=[miller_x, miller_y, miller_z],
        layers=layers,
        vacuum=vacuum,
    )

    in_mem_files = []
    images = []
    for cif_image in cif_images:
        mem_file = StringIO.StringIO()
        mem_file.write(cif_image)
        mem_file.seek(0)
        atoms = ase.io.read(mem_file, format='cif')
        images.append(atoms)

    sites_list = []

    alt_labels = []
    cif_images = []
    site_names = []
    site_types = []
    error_message = ''
    atoms_objects = []
    for atoms_i, atoms in enumerate(copy.deepcopy(images)):
        gen = catkit.surface.SlabGenerator(
            bulk=bulk_atoms,
            miller_index=[miller_x, miller_y, miller_z, ],
            layers=layers,
            vacuum=vacuum,
        )
        atoms = gen.get_slab(primitive=True)
        sites = gen.adsorption_sites(
            atoms,
            symmetry_reduced=True,
        )

        label_index = 0
        alt_labels.append({})
        for adsorbate_site_label in sorted(sites):
            site_types.append(adsorbate_site_label)
            if site_type != 'all' and adsorbate_site_label != site_type:
                continue
            for adsorbate_site_i, adsorbate_site in enumerate(sites[adsorbate_site_label][0]):
                if len(adsorbate_site) == 0:
                    continue  # skip empty sites
                atoms = gen.get_slab(primitive=True)

                for site_label_i, site_label in enumerate(sites):

                    for site_i, site in enumerate(sites[site_label][0]):
                        if adsorbate_site_label == site_label and adsorbate_site_i == site_i:
                            atoms += ase.atom.Atom(adsorbate,
                                                   site + [0., 0., 1.5])

                        elif place_holder in ase.atoms.chemical_symbols:
                            if site_type != 'all' and site_label != site_type:
                                continue
                            atoms += ase.atom.Atom(place_holder,
                                                   site + [0., 0., 1.5])

                        natoms = len(atoms) - 1
                        alt_labels[-1][len(atoms) - 1] = site_label + \
                            ' ' + str(site_label_i)
                        label_index += 1

                site_names.append(
                    '{adsorbate_site_label}{adsorbate_site_i}'.format(**locals()))

                if return_atoms:
                    atoms_objects.append(atoms)
                else:

                    with StringIO.StringIO() as f:
                        ase.io.write(f, atoms, format='cif')
                        cif_images.append(f.getvalue())

    if return_atoms:
        return ({
            'data': (sites_list),
            'images': atoms_objects,
            'site_types': site_types,
            'site_names': site_names,
            'altLabels': alt_labels,
            'error': error_message
        })
    else:
        return flask.jsonify({
            'data': (sites_list),
            'cifImages': cif_images,
            'site_types': site_types,
            'site_names': site_names,
            'altLabels': alt_labels,
            'error': error_message
        })


@catKitDemo.route('/place_adsorbates', methods=['GET', 'POST'])
def place_adsorbates(request=None, return_atoms=False, place_holder='F'):
    request = flask.request if request is None else request
    if type(request.args) is str:
        request.args = json.loads(request.args)

    if type(request.args.get('siteOccupations', '{}')) is str:
        site_occupation = json.loads(request.args.get('siteOccupations', '{}'))
    else:
        site_occupation = request.args.get('siteOccupations', {})

    if type(request.args.get('slabParams', '{}')) is str:
        slab_params = json.loads(request.args.get('slabParams', '{}'))
    else:
        slab_params = request.args.get('slabParams', {})

    miller_x = int(slab_params.get('millerX', 1))
    miller_y = int(slab_params.get('millerY', 1))
    miller_z = int(slab_params.get('millerZ', 1))
    layers = int(slab_params.get('layers', 4))
    axis = int(slab_params.get('axis', 2))
    vacuum = float(slab_params.get('vacuum', 10.))

    cif_images = json.loads(generate_slab_cif(request).data)['images']

    if type(request.args.get('adsorbateParams', '{}')) is str:
        adsorbate_params = json.loads(
            request.args.get('adsorbateParams', '{}'))
    else:
        adsorbate_params = request.args.get('adsorbateParams', {})

    site_type = str(adsorbate_params.get('siteType', 'all'))
    adsorbate = str(adsorbate_params.get('adsorbate', 'empty'))

    bulk_atoms = generate_bulk_cif(request, return_atoms=True)

    with StringIO.StringIO() as f:
        ase.io.write(f, bulk_atoms, format='py')
        _batoms = '='.join(f.getvalue().split('=')[1:])

    gen = catkit.surface.SlabGenerator(
        bulk=bulk_atoms,
        miller_index=[miller_x, miller_y, miller_z
                      ],
        layers=layers,
    )

    in_mem_files = []
    images = []
    for cif_image in cif_images:
        mem_file = StringIO.StringIO()
        mem_file.write(cif_image)
        mem_file.seek(0)
        atoms = ase.io.read(mem_file, format='cif')
        images.append(atoms)

    sites_list = []
    #site_occupation = json.loads(request.args.get('siteOccupation', {}))

    for i, atoms in enumerate(images):
        atoms0 = atoms
        gen = catkit.surface.SlabGenerator(
            bulk=bulk_atoms,
            miller_index=[miller_x, miller_y, miller_z],
            layers=layers,
            vacuum=vacuum,
        )
        atoms = gen.get_slab(primitive=True)
        sites = gen.adsorption_sites(
            atoms, symmetry_reduced=True,
        )
        for adsorbate_site_label in sorted(sites):
            if site_type != 'all' and adsorbate_site_label != site_type:
                continue
            for adsorbate_site_i, adsorbate_site in enumerate(sites[adsorbate_site_label][0]):
                if len(adsorbate_site) == 0:
                    continue  # skip empty sites
                atoms = gen.get_slab(primitive=True)

                for site_label_i, site_label in enumerate(sites):

                    for site_i, site in enumerate(sites[site_label][0]):
                        if adsorbate_site_label == site_label and adsorbate_site_i == site_i:
                            atoms += ase.atom.Atom(adsorbate,
                                                   site + [0., 0., 1.5])

                        elif place_holder in ase.atoms.chemical_symbols:
                            if site_type != 'all' and site_label != site_type:
                                continue
                            atoms += ase.atom.Atom(place_holder,
                                                   site + [0., 0., 1.5])

        images[i] = atoms

    mem_files = []
    #images = []
    for atoms in images:
        mem_files.append(StringIO.StringIO())
        ase.io.write(mem_files[-1], atoms, format='cif')
        mem_files[-1].seek(0)

    if return_atoms:
        return images

    return flask.jsonify({
        'images': [mem_file.getvalue() for mem_file in mem_files],
        'n': len(images),
        'cif_images': cif_images,
    })


@catKitDemo.route('/generate_dft_input', methods=['GET', 'POST'])
def generate_dft_input(request=None):
    request = flask.request if request is None else request
    if type(request.args) is str:
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
        '{"volume": "",\n"publisher": "",\n"doi": "",\n"title": "",\n"journal": "",\n"authors": [],\n"year": "",\n"number": "",\n"pages": ""}\n')
#

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
    stoichiometry_factors = apps.utils.gas_phase_references.get_stoichiometry_factors(
        adsorbate_names, references)

    for i, calculation in enumerate(calculations):
        bulk_params = (calculation.get('bulkParams', {}))
        slab_params = (calculation.get('slabParams', {}))
        adsorbate_params = (calculation.get('adsorbateParams', {}))
        site_occupation = (calculation.get('siteOccupations', {}))
        dft_params = (calculation.get('dftParams', {}))

        # Unpack a little further ...
        miller_x = slab_params.get('millerX', 'N')
        miller_y = slab_params.get('millerY', 'N')
        miller_z = slab_params.get('millerZ', 'N')
        facet = '{miller_x}{miller_y}{miller_z}'.format(**locals())

        composition = ''.join(bulk_params.get('elements', []))
        structure = bulk_params.get('structure', '')

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
        #print("Calculation {i}".format(**locals()))

        # 0. Construct ASE DFT Calculator
        #######################

        # 3. Add adsorbates
        #################################
        adsorbates = get_adsorption_sites(
            mock_request, return_atoms=True, place_holder='empty')
        images = adsorbates['images']
        site_names = adsorbates['site_names']
        adsorbates_strings = []
        for image_i, image in enumerate(images):
            # Generate Adsorbates String
            adsorbate = str(adsorbate_params.get('adsorbate', 'empty'))
            reactants = []
            for molecule, factor in stoichiometry_factors[adsorbate].items():
                reactants.append('{factor}{molecule}gas'.format(**locals()))
                gas_phase_molecules.add(molecule)

            reactants = '_'.join(reactants)
            site_name = site_names[image_i]
            equation = 'star{site_name}_{reactants}__{adsorbate}star{site_name}'.format(
                **locals())
            adsorbates = '{adsorbate}star{site_name}'.format(**locals())

            adsorbates_strings.append(adsorbates)
            slab_path = '{calcstr}/{dft_params[calculator]}/{dft_params[functional]}/{composition}_{structure}/{facet}/{equation}'.format(
                **locals())

            with StringIO.StringIO() as mem_file:
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
                for molecule, factor in stoichiometry_factors[adsorbate].items():

                    reactants.append(
                        '{factor}{molecule}gas'.format(**locals()))
                reactants = '_'.join(reactants)
                site_name = site_names[image_i]
                equation = 'star{site_name}_{reactants}__{adsorbate}star{site_name}'.format(
                    **locals())

                adsorbates = '{adsorbate}star{site_name}'.format(**locals())
                slab_path = '{calcstr}/{dft_params[calculator]}/{dft_params[functional]}/{composition}_{structure}/{facet}/star.{SUFFIX}'.format(
                    **locals())

                if not slab_path in zf.namelist():
                    with StringIO.StringIO() as mem_file:
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
            equation = 'star{site_name}_{reactants}__{adsorbate}star{site_name}'.format(
                **locals())

            bulk_path = '{calcstr}/{dft_params[calculator]}/{dft_params[functional]}/{composition}_{structure}/{composition}_bulk.{SUFFIX}'.format(
                **locals())

            if not bulk_path in zf.namelist():
                with StringIO.StringIO() as mem_file:
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
            molecule_path = '{calcstr}/{dft_params[calculator]}/{dft_params[functional]}/gas/{molecule_name}_gas.{SUFFIX}'.format(
                **locals())

            if not molecule_path in zf.namelist():
                with StringIO.StringIO() as mem_file:
                    ase.io.write(mem_file, molecule, format=SUFFIX)
                    zf.writestr(molecule_path, mem_file.getvalue())

    #zf.compress_type = zipfile.ZIP_DEFLATED
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
    out_format = request.args.get('format',
                                  request.get_json().get('params', {}).get('format', '')
                                  )

    if not out_format:
        out_format = 'cif'
    if out_format not in VALID_OUT_FORMATS:
        return {
            "error": "outFormat {outformat} is invalid. Should be on of {VALID_OUT_FORMATS}".format(**locals()),
        }

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
        out_file.name = 'CatApp Browser Export'
        ase.io.write(out_file, atoms, out_format)
        out_content = out_file.getvalue()

    format2extension = {value: key for key,
                        value in ase.io.formats.extension2format.items()}

    extension = format2extension.get(out_format, out_format)

    return flask.jsonify({
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
        'message': message,
    })