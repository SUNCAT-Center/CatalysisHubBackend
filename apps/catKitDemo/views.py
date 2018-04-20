import flask
import os
import os.path
import csv
import sys
import zipfile

# print(os.path.abspath('./CatKit/.'))
# sys.path.append(os.path.abspath('./CatKit/.'))
# for path in sys.path:
# print(path)
#import catkit
#import catkit.surface

import pprint
import time

try:
    import io as StringIO
except:
    import StringIO


import ase.io
import ase.build
import ase.io.espresso


def index():
    return "You are at catKitDemo root. Nothing to see here."


def generate_bulk_cif():
    data = flask.request.get_json() or {}
    cubic = (data.get('cubic', 'true').lower() == 'true')
    structure = data.get('structure', 'fcc')
    lattice_constant = float(data.get('lattice_constant', 4.0))
    element1 = data.get('element1', 'Pt')
    element2 = data.get('element2', 'Pt')
    element3 = data.get('element3', 'Pt')
    element4 = data.get('element4', 'Pt')
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


def generate_slab_cif():
    data = flask.request.get_json() or {}
    miller_x = int(data.get('miller_x', 1))
    miller_y = int(data.get('miller_y', 1))
    miller_z = int(data.get('miller_z', 1))
    layers = int(data.get('layers', 4))
    axis = int(data.get('axis', 2))
    vacuum = float(data.get('vacuum', 10.))
    bulk_cif = data.get('bulk_cif', '')

    mem_file = StringIO.StringIO()
    mem_file.write(bulk_cif)
    mem_file.seek(0)

    atoms = ase.io.read(mem_file, format='cif')

    Gen = catkit.surface.SlabGenerator(atoms,
                                       [
                                           miller_x,
                                           miller_y,
                                           miller_z
                                       ])
    terminations = Gen.get_unique_terminations()
    images = []
    mem_files = []
    for (iterm, term) in enumerate(terminations):
        images.append(Gen.get_slab(layers=layers, iterm=iterm))
        images[-1].center(axis=axis, vacuum=vacuum)
        mem_files.append(StringIO.StringIO())
        ase.io.write(mem_files[-1], images[-1], format='cif')
        mem_files[-1].seek(0)

    return flask.jsonify({
        'images': [mem_file.getvalue() for mem_file in mem_files],
    })


def generate_dft():
    data = flask.request.get_json() or {}

    calculator = str(data.get('calculator', 'espresso'))
    functional = str(data.get('functional', 'PBE'))
    miller_x = int(data.get('miller_x', 1))
    miller_y = int(data.get('miller_y', 1))
    miller_z = int(data.get('miller_z', 1))
    layers = int(data.get('layers', 4))
    layers = int(data.get('layers', 4))
    axis = int(data.get('axis', 2))
    vacuum = float(data.get('vacuum', 10.))
    structure = data.get('structure', 'fcc')
    lattice_constant = float(data.get('lattice_constant', 4.0))
    element1 = data.get('element1', 'Pt')
    element2 = data.get('element2', 'Pt')
    element3 = data.get('element3', 'Pt')
    element4 = data.get('element4', 'Pt')

    elements = [
        element1,
        element2,
        element3,
        element4,
    ]

    cubic = (data.get('cubic', 'true').lower() == 'true')

    t = int(time.time())

    pname = 'dft_input_{t}'.format(**locals())

    fd = StringIO.BytesIO()

    # Create Template for publication.txt
    zf = zipfile.ZipFile(fd, 'w')
    zf.writestr(
        '{pname}/publication.txt'.format(**locals()),
        '{"volume": "",\n"publisher": "",\n"doi": "",\n"title": "",\n"journal": "",\n"authors": [],\n"year": "",\n"number": "",\n"pages": ""}\n')

    # Create Bulk Input File
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
    ase.io.espresso.write_espresso_in(mem_file, atoms)

    composition = ''.join([
        element1,
        element2,
        element3,
        element4,
    ])
    zf.writestr('{pname}/{calculator}/{functional}/{structure}_{composition}/pw.inp'.format(**locals()),
                mem_file.getvalue()
                )

    # Create Slab Input Files
    miller = ''.join(map(str,
                         [miller_x, miller_y, miller_z]
                         ))

    Gen = catkit.surface.SlabGenerator(atoms,
                                       [
                                           miller_x,
                                           miller_y,
                                           miller_z
                                       ])
    terminations = Gen.get_unique_terminations()
    images = []
    mem_files = []
    for (iterm, term) in enumerate(terminations):
        images.append(Gen.get_slab(layers=layers, iterm=iterm))
        images[-1].center(axis=axis, vacuum=vacuum)
        mem_files.append(StringIO.StringIO())
        ase.io.espresso.write_espresso_in(mem_files[-1], images[-1], )
        mem_files[-1].seek(0)
        zf.writestr('{pname}/{calculator}/{functional}/{structure}_{composition}/{miller}_{iterm}/pw.inp'.format(**locals()),
                    mem_files[-1].getvalue())

    # Close zip file, last before creating HttpResponse
    zf.close()

    response = HttpResponse(
        fd.getvalue(),
        content_type="application/x-zip-compressed",
    )

    response[
        'Content-Disposition'] = 'attachment; filename=dft_input_{t}.zip'.format(**locals())
    return response
