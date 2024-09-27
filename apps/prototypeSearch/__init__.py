# -*- coding: utf-8 -*-
import copy
import pprint
import json
import os
import os.path
import pprint
import zipfile
import time
import datetime
import codecs

try:
    import bulk_enumerator as be
except ImportError:
    print("Warning: could not import bulk_enumerator, check installation.")
    be = None

# workaround to work on both Python 2 and Python 3
try:
    import io as StringIO
except ImportError:
    import StringIO

import numpy as np
from ase.symbols import string2symbols

import flask
from flask_cors import CORS


from apps.prototypeSearch import models
import apps.utils


app = flask.Blueprint('prototypeSearch', __name__)
# app = flask.Flask(__name__)
# cors = CORS(app)
VIEW_NAMES = models.inspector.get_view_names()


def encode(s, name, *args, **kwargs):
    codec = codecs.lookup(name)
    rv, length = codec.encode(s, *args, **kwargs)
    if not isinstance(rv, (str, bytes, bytearray)):
        raise TypeError('Not a string or byte codec')
    return rv


def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def is_float(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def row2dict(row):
    d = {}
    for column in row.__table__.columns:
        d[column.name] = str(getattr(row, column.name))
    return d


def apply_range(query, column, value):
    if not value.count('-') == 1:
        return query
    minimum, maximum = value.split('-')
    if is_float(minimum):
        query = query.filter(
            getattr(models.Geometry, column) >= float(minimum))
    if is_float(maximum):
        query = query.filter(
            getattr(models.Geometry, column) <= float(maximum))
    return query


def expand_str_values(values):
    return values.split(',')


def expand_int_values(values, limit=230):
    values = values.split(',')
    expanded_values = []
    for value in values:
        if value.count('-') == 0:
            expanded_values.append(value)
        elif value.count('-') == 1:
            try:
                start, end = value.split('-')
                start, end = int(start), int(end)
            except ValueError as e:
                print(e)
                pass
            if end > start and (end - start) <= limit:
                expanded_values.extend(list(range(start, end + 1)))
    return expanded_values


def apply_filters(query, search_terms=[], facet_filters=[], ignored_facets=[]):
    """
    **Apply filters against query.**

    Terms are separated by a space (`` ``) and
    results have to match each term (AND).
    If search terms specify a column (``column:value``) they are applied only
    against the respective column. The value can consist of one or more values
    separated by a comma. Numerical ranges can be abbreviated
    with a dash (``-``).

    Values within one column are applied with an OR filter. One example is
    ``spacegroup:160,170-190``. This would match any structure with spacegroup
    160 or any spacegroup larger or equal to 170 and less or equal to 190.

    Possible column names are ``crystal_system``, ``handle``, ``n_atoms``,
    ``n_species``, ``prototype``, ``repository``, ``spacegroup``, ``species``,
    ``stoichiometry``, ``tag``.

    ``crystal_system`` takes values ``triclinic``, ``monoclinic``,
    ``orthorhombic``, ``tetragonal``, ``trigonal``, ``hexagonal``,
    or ``cubic`` and is a short to the
    corresponding range of spacegroups as listed here:
    https://en.wikipedia.org/wiki/List_of_space_groups.

         ``triclinic``
             1 - 2
         ``monoclinic``
             3 - 15
         ``orthorhombic``
             16 - 74
         ``tetragonal``
             75 - 142
         ``trigonal``
             143 - 167
         ``hexagonal``
             168 - 194
         ``cubic``
             195 - 230

    species is a special column in that it allows filtering with
    AND and OR. The term ``species:AuPd`` will filter for structures
    containing Gold AND Palladium, whereas ``species:Au,Pd`` will filter for
    structures containing Au OR Pd.

    Some examples:

        - ``spacegroup:160-222,230``
        - ``species:AuZn n_species:2``
        - ``species:GaGe n_atoms:3``
        - ``species:SrTi stoichiometry:ABC2``
        - ``repository:AMCSD,OCMD``
        - ``crystal_system:tetragonal species:AuPd``

    """
    # FIRST
    # apply each search terms against
    # - handle
    # - spacegroup
    # - species
    # - wyckoffs
    # - prototype
    # - repository
    for search_term in search_terms:
        field_search = False
        tag_search = False
        if ':' in search_term:
            field, value = search_term.split(':')[:2]
            field = field.lower()
            field_search = search_term.split(':')[0] in [
                'crystal_system',
                'handle',
                'n_atoms',
                'n_species',
                'prototype',
                'repository',
                'spacegroup',
                'species',
                'stoichiometry',
                'tag',
                'scarcity',
                'volume',
                'density',
            ]
        elif '*' in search_term:
            search_term = '%' + search_term.replace('*', '%') + '%'
            tag_search = True

        if field_search:
            if field == 'handle':
                query = query.filter(
                    models.Geometry.handle == value,
                )
            elif field == 'volume':
                query = apply_range(query, field, value)
            elif field == 'density':
                query = apply_range(query, field, value)
            elif field == 'scarcity':
                query = apply_range(query, field, value)
            elif field == 'crystal_system':
                spacegroups = []
                for v in value.split(','):
                    if v == 'triclinic':
                        spacegroups.extend(list(range(1, 3)))
                    elif v == 'monoclinic':
                        spacegroups.extend(list(range(3, 16)))
                    elif v == 'orthorhombic':
                        spacegroups.extend(list(range(16, 75)))
                    elif v == 'tetragonal':
                        spacegroups.extend(list(range(75, 143)))
                    elif v == 'trigonal':
                        spacegroups.extend(list(range(143, 168)))
                    elif v == 'hexagonal':
                        spacegroups.extend(list(range(168, 195)))
                    elif v == 'cubic':
                        spacegroups.extend(list(range(195, 231)))
                    else:
                        spacegroups.extend(expand_int_values(v))

                query = query.filter(
                    models.Geometry.spacegroup.in_(spacegroups),
                )

            elif field == 'spacegroup':
                query = query.filter(
                    models.Geometry.spacegroup.in_(expand_int_values(value)),
                )
            elif field == 'species':
                if ',' in value:
                    query = query.filter(models.or_(
                        models.Geometry.species.any(v)
                        for v in expand_str_values(value)
                    )
                    )
                else:
                    value = ','.join(string2symbols(value))
                    query = query.filter(
                        models.Geometry.species.contains('{' + value + '}'),
                    )
            elif field == 'tag':
                query = query.filter(
                    models.Geometry.tags.like(
                        '%' + value.lower().replace('*', '%') + '%'),
                )
            elif field == 'prototype':
                query = query.filter(
                    models.Geometry.prototype.in_(expand_str_values(value)),
                )
            elif field == 'repository':
                query = query.filter(
                    models.Geometry.repository.in_(expand_str_values(value)),
                )
                print(expand_str_values(value))
            elif field == 'stoichiometry':
                query = query.filter(
                    models.Geometry.stoichiometry.in_(
                        expand_str_values(value)),
                )
            elif field == 'n_species':
                query = query.filter(
                    models.Geometry.n_species.in_(expand_int_values(value)),
                )
            elif field == 'n_atoms':
                query = query.filter(
                    models.Geometry.n_atoms.in_(expand_int_values(value)),
                )
        else:
            query = query.filter(
                models.Geometry.tags.like(
                    '%' + search_term.lower().replace('*', '%') + '%'),
            )

    # SECOND Apply facet filters
    merged_facet_filters = {}
    for facet_filter in facet_filters:
        field, value = facet_filter.split(':')
        merged_facet_filters.setdefault(field, []).append(value)

    for key, value in merged_facet_filters.items():
        if key not in ignored_facets and key == 'n_atoms':
            query = query.filter(models.or_(*[
                models.Geometry.n_atoms == int(v)
                for v in value
            ]))
        elif key not in ignored_facets and key == 'n_atoms':
            query = query.filter(models.or_(*[
                models.Geometry.n_atoms == int(v)
                for v in value
            ]))
        elif key not in ignored_facets and key == 'n_wyckoffs':
            query = query.filter(models.or_(*[
                models.Geometry.n_wyckoffs == int(v)
                for v in value
            ]))
        elif key not in ignored_facets and key == 'spacegroup':
            query = query.filter(models.or_(*[
                models.Geometry.spacegroup == int(v)
                for v in value
            ]))
        elif key not in ignored_facets and key == 'species':
            query = query.filter(models.or_(*[
                models.Geometry.species.contains('{' + v + '}')
                for v in value
            ]))
        elif key not in ignored_facets and key == 'repository':
            query = query.filter(models.or_(*[
                models.Geometry.repository == v
                for v in value
            ]))
        elif key not in ignored_facets and key == 'stoichiometry':
            query = query.filter(models.or_(*[
                models.Geometry.stoichiometry == v
                for v in value
            ]))

    # pprint.pprint(merged_facet_filters)

    return query


def get_facet(
        facet,
        limit=100,
        offset=0,
        search_terms=[],
        facet_filters=[],
        return_all=True):
    """
    Build facet responses
    Don't apply facet filters here
    because that would defeat the purpose
    """
    if not search_terms \
       and not facet_filters \
       and f'{facet}_facet' in VIEW_NAMES:
        return list(map(tuple,
                        models.engine.execute(
                            f'select * from {facet}_facet '
                            f' limit {limit} offset {offset}'
                        )))
    else:
        query = apply_filters(
            models.session.query(
                getattr(models.Geometry, facet),
                models.func.count(),
            ), search_terms=search_terms,
            facet_filters=facet_filters,
            ignored_facets=[facet]
        ) \
            .group_by(getattr(models.Geometry, facet)) \
            .order_by(models.desc(models.func.count()))

        if return_all:
            return query \
                .offset(offset) \
                .limit(limit) \
                .all()
        else:
            return query


@app.route('/prototype/', methods=['GET', 'POST'])
def prototype(request=None):
    time0 = time.time()
    request = flask.request if request is None else request
    request.values = dict((request.get_json() or {}),
                          **request.values.to_dict(), )
    if isinstance(request.values, str):
        request.values = json.loads(request.values)

    prototype = request.values.get('prototype', '')
    search_terms = request.values.get('search_terms', '').split()
    facet_filters = json.loads(request.values.get('facet_filters', '[]'))
    offset = int(request.values.get('offset', 0))
    limit = int(request.values.get('limit', 1000))

    # Build prototype response
    query = models.session.query(models.Geometry)
    query = apply_filters(query, search_terms, facet_filters)
    query = query \
        .filter(models.Geometry.prototype == prototype) \
        .offset(offset) \
        .limit(limit)
    prototypes = [row2dict(x) for x in query.all()]

    return flask.jsonify({
        'time': time.time() - time0,
        'prototypes': prototypes,
        'input': {
            'prototype': prototype,
            'search_terms': search_terms,
            'facet_filters': facet_filters,
            'offset': offset,
            'limit': limit,
        },
    })


@app.route('/facet_search/', methods=['GET', 'POST'])
def facet_search(request=None):
    """
    Facet search bulk prototypes

    Args:
        Search terms (str)
        Filters (list): List of tuples (field, value).
        Filters are applied against search with an
        OR within field and and
        AND across categories.

    SQlAlchemy Notes:
        - Pagination
            use .limit() and .offset() for pagination

        - Distinct filter
            use .distinct(Geometry.prototype)

        - Query multiple in category with AND
            use .filter(Geometry.species.contains('{Pt,Pd}'))

        - Group by facet
            session.query(
                    Geometry.spacegroup, sqlalchemy.func.count()
                ).group_by(
                    Geometry.spacegroup
                ).order_by(
                    desc(func.count())
                ).limit(10).all()

    """

    time0 = time.time()
    request = flask.request if request is None else request
    request.values = dict((request.get_json() or {}),
                          **request.values.to_dict(), )
    if isinstance(request.values, str):
        request.values = json.loads(request.values)

    search_terms = request.values.get('search_terms', '').split()
    facet_filters = json.loads(request.values.get('facet_filters', '[]'))
    offset = int(request.values.get('offset', 0))
    limit = int(request.values.get('limit', 10))

    # Build prototype response
    prototypes = get_facet(
        'prototype',
        search_terms=search_terms,
        facet_filters=facet_filters,
        limit=limit,
        offset=offset,
    )
    if not search_terms \
            and not facet_filters \
            and 'total_count' in VIEW_NAMES \
            and 'prototype_count' in VIEW_NAMES:
        n_compounds = list(
            models.engine.execute(
                'select * from total_count'
            )
        )[0][0]

        n_prototypes = list(
            models.engine.execute(
                'select * from prototype_count'
            )
        )[0][0]
    else:
        n_compounds = apply_filters(
            models.session.query(models.Geometry),
            search_terms, facet_filters,
        ).count()
        n_prototypes = sum(
            x[1] for x in
            get_facet(
                'prototype',
                limit=limit,
                offset=offset,
                search_terms=search_terms,
                facet_filters=facet_filters,
            ))
    print(time.time() - time0, "AFTER RESULT COUNT")

    # - spacegroup
    spacegroups = get_facet(
        'spacegroup',
        search_terms=search_terms,
        facet_filters=facet_filters,
        limit=230)
    print(time.time() - time0, "AFTER SPACEGROUPS")

    # - n_wyckoffs
    n_wyckoffs = get_facet(
        'n_wyckoffs',
        search_terms=search_terms,
        facet_filters=facet_filters)
    print(time.time() - time0, "AFTER NWYCKOFFS")

    # - n_species
    n_species = get_facet(
        'n_species',
        search_terms=search_terms,
        facet_filters=facet_filters)
    print(time.time() - time0, "AFTER SPECIES")

    # - n_atoms
    n_atoms = get_facet(
        'n_atoms',
        search_terms=search_terms,
        facet_filters=facet_filters)
    print(time.time() - time0, "AFTER NSPECIES")

    # - stoichiometries
    stoichiometries = get_facet(
        'stoichiometry',
        search_terms=search_terms,
        facet_filters=facet_filters)
    print(time.time() - time0, "AFTER STOICHIOMETRY")

    # - repositories
    repositories = get_facet(
        'repository',
        search_terms=search_terms,
        facet_filters=facet_filters)
    print(time.time() - time0, "AFTER REPOSITORIES - DONE")

    # JSONIFY and response
    return flask.jsonify({
        'time': time.time() - time0,
        'input': {
            'offset': offset,
            'limit': limit,
            'search_terms': search_terms,
            'facet_filters': facet_filters,
        },
        'prototypes': prototypes,
        'n_prototypes': n_prototypes,
        'n_compounds': n_compounds,
        'spacegroups': spacegroups,
        'repositories': repositories,
        'n_atoms': n_atoms,
        'n_species': n_species,
        'n_wyckoffs': n_wyckoffs,
        'stoichiometries': stoichiometries,
    })


@app.route('/get_structure/', methods=['POST'])
def get_structure(request=None):
    """
    Return structure as POSCAR string from Spacegroup and Wyckoff parameters.

    Args:
        spacegroup(int): Spacegroup [1-230] as int. Defaults to 225.
        species ([str]): Atomic symbols as list of strings. Defaults to ["Pt"].
        wyckoffs ([str]): List of Wyckoff sites. Defaults to ["a"].
        parameter_names ([str]): List Wyckoff cell parameters.
                                 Defaults to ["a"].
        parameters ([float]): List of Wyckoff cell parameters.
                              Defaults to [2.7].



    Return:
        structure (str): String of POSCAR.
        time (float): Time in seconds required to generate structure.

    Example:

        curl -XPOST   -H "Content-type: application/json"  \
                --data '{}' \
                http://api.catalysis-hub.org/apps/prototypeSearch/get_structure/



    """
    time0 = time.time()
    request = flask.request if request is None else request
    request.values = dict((request.get_json() or {}),
                          **request.values.to_dict(), )
    if isinstance(request.values, str):
        request.values = json.loads(request.values)

    spacegroup = int(request.values.get('spacegroup', 225))
    wyckoffs = json.loads(
        request.values.get('wyckoffs', '["a"]').replace("'", '"'))
    species = json.loads(request.values.get('species', '["Pt"]').replace("'", '"'))
    parameter_names = json.loads(
        request.values.get('parameter_names', '["a"]').replace("'", '"')
    )
    parameters = json.loads(
        request.values.get('parameters', '[2.7]').replace("'", '"'))

    input_params = {
        'spacegroup': spacegroup,
        'wyckoffs': wyckoffs,
        'species': species,
        'parameter_names': parameter_names,
        'parameters': parameters,
    }

    structure = ''
    if be is not None:
        bulk = be.bulk.BULK()
        bulk.set_spacegroup(spacegroup)
        bulk.set_wyckoff(wyckoffs)
        bulk.set_species(species)
        bulk.set_parameter_values(parameter_names, parameters)
        structure = bulk.get_std_poscar()
        bulk.delete()

    return flask.jsonify({
        'time': time.time() - time0,
        'structure': apps.utils.ase_convert(
            structure,
            'vasp',
            'cif'),
        'input': input_params,
    })


if __name__ == '__main__':
    app.run(debug=True, port=5002)
