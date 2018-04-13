import os
import sys
import unittest
import tempfile
import pprint
import sqlite3
import json

import flask

sys.path.append(os.path.abspath('.'))

import app

#def connect_db():
#    rv = sqlite3.connect(app.app.config['DATABASE'])
#    rv.row_factory = sqlite3.Row
#    return rv

#def get_db():
#    if not(hasattr(flask.g, 'sqlite_db')):
#        flask.g.sqlite_db = connect_db()
#    return flask.g.sqlite_db


#def init_db(app):
#    db = get_db()
#    with app.open_resource('tests/pg_sample_data.sql') as f:
#        db.cursor().executescript(f.read().decode())
#    db.commit()


class ReactionBackendTestCase(unittest.TestCase):
    def setUp(self):
        #TEST_DB_FILENAME = './test_database.db'
        #self.db_fd = open(TEST_DB_FILENAME, 'w',)
        #app.app.config['DATABASE'] = TEST_DB_FILENAME
        #self.db_fd, app.app.config['DATABASE'] = 'test_data'
        #os.environ['SQLITE_DB'] = app.app.config['DATABASE']
        app.app.testing = True
        self.app = app.app.test_client()
        #with app.app.app_context():
        #    init_db(app.app)

    def get_data(self, query, verbose=False):
        if verbose == True:
            print('\n\nQUERY {query}'.format(**locals()))
        data = json.loads(
            self.app.post('/graphql?query={query}'.format(**locals())).data.decode('utf8')
                )
        if verbose == True:
            print('DATA')
            pprint.pprint(data)
        return data


    #def tearDown(self):
    #    #os.close(self.db_fd)
    #    self.db_fd.close()
    #    os.unlink(app.app.config['DATABASE'])


    def test_graphql1(self):
        #rv = self.app.post('/graphql?query={systems(last: 10){no}}')

        """ systems table"""
        # TEST that some systems are returned
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId } } }}')
        assert 'data' in rv_data
        assert 'systems' in rv_data['data']
        assert 'edges' in rv_data['data']['systems']
        assert len(rv_data['data']['systems']['edges']) == 10

        # test that the right number of systems is returned
        rv_data = self.get_data('{systems { edges { node { uniqueId } } }}')
        assert len(rv_data['data']['systems']['edges']) == 3316, "Found " + str(len(rv_data['data']['systems']['edges'])) + " systems instead of 3316"

        ## assert that unique id has 32 characters
        #uniqueId = rv_data['data']['systems']['edges'][0]['node']['uniqueId']
        #assert len(uniqueId) == 32, "len(uniqueId) == " + str(len(uniqueId)) + " instead of 32"

        #rv_data = self.get_data("{systems(uniqueId: \"" + uniqueId + "\") { edges { node { Cifdata } } }}")
        
        ##pprint.pprint(rv_data)
        ## TODO: Current CifData is None
        ##       Analyze and consider fixing

    def test_graphql2(self):
        # TEST that 10 elements with energy are returned
        rv_data = self.get_data("{systems(last: 10 ) { edges { node { energy Cifdata } } }}")
        #pprint.pprint(rv_data)
        
        assert len(rv_data['data']['systems']['edges']) == 10
        for node in rv_data['data']['systems']['edges']:
            assert node['node']['energy'] < 10

    def test_graphql3(self):
        # TEST that querying for years, gives meaningful in publications
        #query = '{numberKeys(last: 10, key:"publication_year") { edges { node { value } } }'
        #rv_data = self.get_data(query)
        
        """ Publications"""

        # TEST if we can filter publications by year
        query = '{publications(last: 10, year: 2017) { edges { node { title year doi } } }}'
        rv_data = self.get_data(query)
        results = rv_data['data']['publications']['edges']
        assert 'node' in results[0]
        assert 'title' in results[0]['node']
        assert 'doi' in results[0]['node']

    def test_graphql4(self):
        # TEST if we can call reactions table from publications
        query ='{publications(year: 2017, last: 1) {edges {node { doi journal reactions { dftCode dftFunctional } } } }}'
        rv_data = self.get_data(query)
        results = rv_data['data']['publications']['edges']

        assert results[0]['node']['doi'] == '10.1021/acs.jpcc.7b02383', results[0]['node']['doi']
        assert results[0]['node']['journal']  == 'JPCC', results[0]['node']['journal']
        results_reactions = results[0]['node']['reactions']
        assert results_reactions[0]['dftCode'] == 'Quantum ESPRESSSO', results_reactions[0]['dftCode']
        assert results_reactions[0]['dftFunctional'] == 'RPBE', results_reactions[0]['dftFunctional']

    def test_order_key(self):
        query ='{systems(last: 1, order: "energy") {edges {node { Formula energy} } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['systems']['edges'][0]['node']['Formula'] == 'H2', rv_data

    def test_order_key_descending(self):
        query ='{systems(last: 1, order: "-energy") {edges {node { Formula energy} } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['systems']['edges'][0]['node']['Formula'] == 'Cu36Zn3', rv_data

    def test_total_count(self):
        query ='{systems(first: 0) { totalCount edges { node { id } } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['systems']['totalCount'] == 3316, rv_data


    def test_resolve_publication_systems(self):
        query ='{publications(year: 2017, last: 1) { totalCount edges {node { systems { uniqueId } } } }}'
        rv_data = self.get_data(query)
        assert len(rv_data['data']['publications']['edges'][0]['node']['systems']) == 7, rv_data

    def test_resolve_input_file(self):
        query ='{systems(last: 1, order: "-energy") {edges {node { Formula energy InputFile(format: "vasp")} } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['systems']['edges'][0]['node']['InputFile'].strip(), rv_data

    def test_resolve_input_file_undefined(self):
        query ='{systems(last: 1, order: "-energy") {edges {node { Formula energy InputFile(format: "blablabla")} } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['systems']['edges'][0]['node']['InputFile'].strip().startswith('Unsupported'), rv_data

    def test_resolve_reaction_systems(self):
        query ='{reactions(first:1, order:"reactionEnergy") { edges { node { reactionEnergy systems { id Formula } } } }}'
        rv_data = self.get_data(query)
        assert len(rv_data['data']['reactions']['edges'][0]['node']['systems']) == 3, rv_data

    def test_distinct_filter_on(self):
        query = '{reactions(first: 0, reactants:"~H", distinct: true) { totalCount edges { node { id } } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['reactions']['totalCount'] == 129, rv_data

    def test_distinct_filter_off(self):
        query = '{reactions(first: 0, reactants:"~H", distinct: false) { totalCount edges { node { id } } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['reactions']['totalCount'] == 3297, rv_data

    def test_operation_eq(self):
        query = '{systems(natoms:70, op:"eq" first: 3) { totalCount edges { node { id natoms Formula } } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['systems']['totalCount'] == 2, rv_data

    def test_operation_gt(self):
        query = '{systems(natoms:70, op:"gt" first: 3) { totalCount edges { node { id natoms Formula } } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['systems']['totalCount'] == 52, rv_data

    def test_operation_ge(self):
        query = '{systems(natoms:70, op:"ge" first: 3) { totalCount edges { node { id natoms Formula } } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['systems']['totalCount'] == 54, rv_data

    def test_operation_le(self):
        query = '{systems(natoms:70, op:"le" first: 3) { totalCount edges { node { id natoms Formula } } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['systems']['totalCount'] == 3264, rv_data

    def test_operation_lt(self):
        query = '{systems(natoms:70, op:"lt" first: 3) { totalCount edges { node { id natoms Formula } } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['systems']['totalCount'] == 3262, rv_data

    def test_operation_ne(self):
        query = '{systems(natoms:70, op:"ne" first: 3) { totalCount edges { node { id natoms Formula } } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['systems']['totalCount'] == 3314, rv_data

    def test_reactants_expansion(self):
        query = '{reactions(first:0, reactants: "CO") { totalCount edges { node { id } } }}'
        rv_data = self.get_data(query)
        assert False, rv_data

    def test_reactants_star(self):
        query = '{reactions(first:0, reactants: "COstar") { totalCount edges { node { id } } }}'
        rv_data = self.get_data(query)
        assert False, rv_data

    def test_products_star(self):
        query = '{reactions(first:0, products: "COstar") { totalCount edges { node { id } } }}'
        rv_data = self.get_data(query)
        assert False, rv_data






if __name__ == '__main__':
    unittest.main()
