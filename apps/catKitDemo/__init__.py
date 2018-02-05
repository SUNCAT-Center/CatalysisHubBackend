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


import catkit
import catkit.surface

catKitDemo = flask.Blueprint('catKitDemo', __name__)

VALID_OUT_FORMATS = ["abinit", "castep-cell", "cfg", "cif", "dlp4", "eon", "espresso-in", "extxyz", "findsym",
                     "gen", "gromos", "json", "jsv", "nwchem", "proteindatabank", "py", "turbomole", "v-sim", "vasp", "xsf", "xyz"]


@catKitDemo.route('/generate_bulk_cif/', methods=['GET', 'POST'])
def generate_bulk_cif(request=None):
    request = flask.request if request is None else request
    if type(request.args) is str:
        request.args = json.loads(request.args)

    cubic = json.loads(request.args.get('bulkParams', '{}')).get(
        'cubic', 'true').lower() == 'true'
    structure = json.loads(request.args.get(
        'bulkParams', '{}')).get('structure', 'fcc')
    lattice_constant = float(json.loads(request.args.get(
        'bulkParams', '{}')).get('lattice_constant', 4.0))

    elements = json.loads(request.args.get('bulkParams', '{}')).get('elements')
    pprint.pprint(json.loads(request.args.get('bulkParams', '{}')))

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

    return flask.jsonify({
        'cifdata': mem_file.getvalue(),
    })


@catKitDemo.route('/generate_slab_cif/', methods=['GET', 'POST'])
def generate_slab_cif(request=None):
    request = flask.request if request is None else request
    if type(request.args) is str:
        request.args = json.loads(request.args)

    miller_x = int(json.loads(request.args.get(
        'slabParams', '{}')).get('miller_x', 1))
    miller_y = int(json.loads(request.args.get(
        'slabParams', '{}')).get('miller_y', 1))
    miller_z = int(json.loads(request.args.get(
        'slabParams', '{}')).get('miller_z', 1))
    layers = int(json.loads(request.args.get(
        'slabParams', '{}')).get('layers', 4))
    axis = int(json.loads(request.args.get('slabParams', '{}')).get('axis', 2))
    vacuum = float(json.loads(request.args.get(
        'slabParams', '{}')).get('vacuum', 10.))
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
        images.append(Gen.get_slab(iterm=iterm))
        images[-1].center(axis=axis, vacuum=vacuum)
        mem_files.append(StringIO.StringIO())
        ase.io.write(mem_files[-1], images[-1], format='cif')
        mem_files[-1].seek(0)

    return flask.jsonify({
        'images': [mem_file.getvalue() for mem_file in mem_files],
    })


@catKitDemo.route('/get_adsorption_sites', methods=['GET', 'POST'])
def get_adsorption_sites(request=None):
    request = flask.request if request is None else request
    if type(request.args) is str:
        request.args = json.loads(request.args)

    pprint.pprint(request.args)

    miller_x = int(json.loads(request.args.get(
        'slabParams', '{}')).get('miller_x', 1))
    miller_y = int(json.loads(request.args.get(
        'slabParams', '{}')).get('miller_y', 1))
    miller_z = int(json.loads(request.args.get(
        'slabParams', '{}')).get('miller_z', 1))
    layers = int(json.loads(request.args.get(
        'slabParams', '{}')).get('layers', 4))
    axis = int(json.loads(request.args.get('slabParams', '{}')).get('axis', 2))
    vacuum = float(json.loads(request.args.get(
        'slabParams', '{}')).get('vacuum', 10.))
    bulk_cif = str(request.args.get(
        'bulk_cif', (json.loads(generate_bulk_cif(request).data)['cifdata'])))
    cif_images = json.loads(generate_slab_cif(request).data)['images']

    place_holder = str(json.loads(request.args.get(
        'adsorbateParams', '{}')).get('placeHolder', 'F'))

    site_type = str(json.loads(request.args.get(
        'adsorbateParams', '{}')).get('siteType', 'all'))

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
    for atoms in copy.deepcopy(images):
        gen = catkit.surface.SlabGenerator(
            bulk=bulk_atoms,
            miller_index=[miller_x, miller_y, miller_z
                          ],
            layers=layers,
            vacuum=vacuum,
        )
        atoms = gen.get_slab(primitive=True)
        sites = gen.adsorption_sites(
            atoms,
            symmetry_reduced=True,
        )
        sites_list.append(sites)
        label_index = 0
        alt_labels.append({})
        for site_label in sorted(sites):
            if site_type != 'all' and site_label != site_type:
                continue
            for site_label_i, site in enumerate(sites[site_label][0]):
                if len(site) > 0:
                    atoms += ase.atom.Atom(place_holder, site + [0., 0., 1.5])
                    natoms = len(atoms) - 1
                    alt_labels[-1][len(atoms) - 1] = site_label + \
                        ' ' + str(site_label_i)
                    label_index += 1

        with StringIO.StringIO() as f:
            ase.io.write(f, atoms, format='cif')
            cif_images.append(f.getvalue())

    # serialize numpy arrays
    # for i, sites in enumerate(sites_list):
        # for j, site_name in enumerate(sites):
            # for k, site in enumerate(sites_list[i][site_name]):
            # if type(site) is np.ndarray:
            #sites_list[i][site_name][k] = site.tolist()

    return flask.jsonify({
        'data': (sites_list),
        'cifImages': cif_images,
        'altLabels': alt_labels,
    })


@catKitDemo.route('/place_adsorbates', methods=['GET', 'POST'])
def place_adsorbates(request=None):
    request = flask.request if request is None else request
    if type(request.args) is str:
        request.args = json.loads(request.args)

    miller_x = int(json.loads(request.args.get(
        'slabParams', '{}')).get('miller_x', 1))
    miller_y = int(json.loads(request.args.get(
        'slabParams', '{}')).get('miller_y', 1))
    miller_z = int(json.loads(request.args.get(
        'slabParams', '{}')).get('miller_z', 1))
    layers = int(json.loads(request.args.get(
        'slabParams', '{}')).get('layers', 4))
    axis = int(json.loads(request.args.get('slabParams', '{}')).get('axis', 2))
    vacuum = float(json.loads(request.args.get(
        'slabParams', '{}')).get('vacuum', 10.))
    bulk_cif = str(request.args.get(
        'bulk_cif', (json.loads(generate_bulk_cif(request).data)['cifdata'])))
    cif_images = json.loads(generate_slab_cif(request).data)['images']

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
    site_occupation = json.loads(request.args.get('siteOccupation', {}))

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
        for k in sorted(sites):
            v = sites[k]
            if len(v) != 3:
                continue
            positions, points, _ = v
            lp = len(positions)

            for j, site in enumerate(positions):
                occupation = site_occupation.get(str(i), {}).get(str(k), {})[j]
                if occupation != 'empty':
                    atoms += ase.atoms.Atoms(occupation,
                                             [site + np.array([0, 0, 1.5])])
                else:
                    atoms += ase.atoms.Atoms('F',
                                             [site + np.array([0, 0, 1.5])])
        images[i] = atoms

    mem_files = []
    #images = []
    for atoms in images:
        mem_files.append(StringIO.StringIO())
        ase.io.write(mem_files[-1], atoms, format='cif')
        mem_files[-1].seek(0)

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

    # Unpack request
    ####################
    calculations = json.loads(request.args.get('calculations', '[]'))
    for calculation in calculations:
        bulkParams = json.loads(calculation.get('bulk_params', '{}'))
        slabParams = json.loads(calculation.get('slab_params', '{}'))
        site_occupation = json.loads(calculation.get('siteOccupation', '{}'))
        dft_input = json.loads(calculation.get('dftInput', '{}'))

    # Generate Zip File
    ####################
    timestr = time.strftime(
        "%Y%m%d_%H%M%S", datetime.datetime.now().timetuple())
    calcstr = "calculations_{timestr}".format(**locals())
    mem_file = StringIO.BytesIO()
    zf = zipfile.ZipFile(mem_file, 'w')
    zf.writestr(
        '{calcstr}/publication.txt'.format(**locals()),
        '{"volume": "",\n"publisher": "",\n"doi": "",\n"title": "",\n"journal": "",\n"authors": [],\n"year": "",\n"number": "",\n"pages": ""}\n')

    # Here be Dragons
    ####################

    zf.close()
    mem_file.seek(0)
    response = flask.send_file(
        mem_file,
        attachment_filename="{calcstr}.zip".format(**locals()),
    )

    response.headers[
        u"Content-Disposition"] = 'attachment; filename="{calcstr}.zip"'.format(**locals())
    return response


@catKitDemo.route('/convert_atoms/', methods=['GET', 'POST'])
def convert_atoms(request=None):
    import ase.io
    import ase.io.formats
    request = flask.request if request is None else request
    filename = request.files['file'].filename
    out_format = None
    #out_format = request.files['outFormat']

    if not out_format:
        out_format = 'cif'
    if out_format not in VALID_OUT_FORMATS:
        return {
            "error": "outFormat {outformat} is invalid. Should be on of {VALID_OUT_FORMATS}".format(**locals()),
        }

    with StringIO.BytesIO() as in_bfile:
        request.files['file'].save(in_bfile)
        with StringIO.StringIO() as in_file:
            content = in_file.getvalue()
            in_bfile.seek(0)
            try:
                in_file.write(in_bfile.getvalue().decode('UTF-8'))
            except Exception as error:
                in_file = in_bfile
                # return flask.jsonify({
                #'error': 'Binary files not supported, yet.\n{error}'.format(**locals())
                #})
            in_file.seek(0)
            filetype = ase.io.formats.filetype(filename, read=False)
            # Monkey-patching ase.io.formats
            if filetype == 'inp':
                filetype = 'espresso-in'
            print("FILETYPE '{filetype}'".format(**locals()))
            try:
                atoms = ase.io.read(
                    filename=in_file,
                    index=None,
                    format=filetype,
                )
            except Exception as error:
                if filetype == 'espresso-in':
                    return flask.jsonify({
                        'error': 'Upload Error: Need QE >=5.3 Input File.'.format(**locals())
                    })
                return flask.jsonify({
                    'error': 'Upload Error: filetype = {filetype}\n{error}'.format(**locals())
                })
            with StringIO.StringIO() as out_file:
                out_file.name = 'CatApp Browser Export'
                ase.io.write(out_file, atoms, out_format)
                out_content = out_file.getvalue()

    return flask.jsonify({
        'image': str(out_content),
        'input_filetype': filetype,
        'output_filetype': out_format,
        'filename': filename,
    })


@catKitDemo.route('/upload_dataset/', methods=['GET', 'POST'])
def upload_dataset(request=None):
    request = flask.request if request is None else request
    filename = request.files['file'].filename
    print(filename)
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
