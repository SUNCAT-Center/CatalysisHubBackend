#!/usr/bin/env python

import flask

from apps.catKitDemo import views
catKitDemo = flask.Blueprint('apps/catKitDemo', __name__)

try:
    import io as StringIO
except:
    import StringIO


@catKitDemo.route('/', methods=['GET', 'POST'])
def index():
    return views.index()


@catKitDemo.route('/generate_bulk_cif', methods=['GET', 'POST'])
def generate_bulk_cif():
    return views.generate_bulk_cif()


@catKitDemo.route('/generate_slab_cif')
def generate_slab_cif():
    return views.generate_slab_cif()


@catKitDemo.route('/generate_dft')
def generate_dft():
    return views.generate_dft()
