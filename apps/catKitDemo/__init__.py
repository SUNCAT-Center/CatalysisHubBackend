import flask
import pprint
import json

try:
    import io as StringIO
except:
    import StringIO

import numpy as np

import ase.atoms
import ase.io
import ase.build


import catkit
import catkit.surface

catKitDemo = flask.Blueprint('catKitDemo', __name__)


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
    element1 = json.loads(request.args.get(
        'bulkParams', '{}')).get('element1', 'Pt')
    element2 = json.loads(request.args.get(
        'bulkParams', '{}')).get('element2', 'Pt')
    element3 = json.loads(request.args.get(
        'bulkParams', '{}')).get('element3', 'Pt')
    element4 = json.loads(request.args.get(
        'bulkParams', '{}')).get('element4', 'Pt')
    elements = [
        element1,
        element2,
        element3,
        element4,
    ]

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
    for atoms in images:
        sites = gen.get_adsorption_sites(atoms)
        sites_list.append(sites)

    # serialize numpy arrays
    for i, sites in enumerate(sites_list):
        for j, site_name in enumerate(sites):
            for k, site in enumerate(sites_list[i][site_name]):
                if type(site) is np.ndarray:
                    sites_list[i][site_name][k] = site.tolist()

    return flask.jsonify({
        'data': (sites_list),
        'cif_images': cif_images,
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
        sites = gen.get_adsorption_sites(atoms)
        for k, v in sites.items():
            positions, points = v
            for j, site in enumerate(positions):
                occupation = site_occupation.get(str(i), {}).get(str(k), {})[j]
                if occupation != 'empty':
                    atoms += ase.atoms.Atoms(occupation,
                                             [site + np.array([0, 0, 1.5])])

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
