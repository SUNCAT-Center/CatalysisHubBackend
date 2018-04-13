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
        assert rv_data['data']['reactions']['totalCount'] == 428, rv_data

    def test_reactants_star(self):
        query = '{reactions(first:0, reactants: "COstar") { totalCount edges { node { id } } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['reactions']['totalCount'] == 27, rv_data

    def test_products_star(self):
        query = '{reactions(first:0, products: "COstar") { totalCount edges { node { id } } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['reactions']['totalCount'] == 756, rv_data

    def test_root_website(self):
        rv = self.app.get('/')
        assert rv.status_code == 302 , rv


    def test_root_website(self):
        rv = self.app.get('/apps/')
        assert rv.status_code == 200 , rv

    def test_dft_code_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId DftCode } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['DftCode'] == '', rv_data

    def test_dft_functional_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId DftFunctional } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['DftFunctional'] == '', rv_data

    def test_facet_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId Facet } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Facet'] == '1x1x1', rv_data

    def test_username_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId Username } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Username'] == '', rv_data

    def test_adsorbate_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId Adsorbate } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Adsorbate'] == '', rv_data

    def test_reaction_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId Reaction } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Reaction'] == '', rv_data

    def test_substrate_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId Substrate } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Substrate'] == '', rv_data

    def test_charges_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId Charges } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Charges'] == None, rv_data

    def test_magmoms_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId Magmoms } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Magmoms'] == '[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]', rv_data

    def test_stress_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId Stress } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Stress'] == None, rv_data

    def test_dipole_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId Dipole } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Dipole'] == None, rv_data

    def test_forces_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId Forces } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Forces'] == '[[ 0.          0.          0.        ]\n [ 0.          0.          0.        ]\n [ 0.          0.          0.        ]\n [ 0.          0.          0.        ]\n [ 0.          0.          0.        ]\n [ 0.          0.          0.        ]\n [ 0.          0.          0.        ]\n [ 0.          0.          0.        ]\n [ 0.          0.          0.        ]\n [ 0.          0.          0.        ]\n [ 0.          0.          0.        ]\n [ 0.          0.          0.        ]\n [-0.01465996 -0.01466158  0.03802024]\n [-0.0006968   0.00742852  0.00773271]\n [ 0.0104296  -0.00075254  0.03104007]\n [-0.02258781 -0.00894088  0.00446159]\n [-0.02590547  0.01889229 -0.0289584 ]\n [-0.0004256   0.0044127  -0.0189839 ]\n [ 0.00803226  0.01834773 -0.02640747]]', rv_data

    def test_momenta_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId Momenta } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Momenta'] == None, rv_data

    def test_tags_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId Tags } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Tags'] == '[9 9 9 9 8 8 8 8 7 7 7 7 5 6 1 6 0 0 0]', rv_data

    def test_masses_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId Masses } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Masses'] == None, rv_data

    def test_initial_charges_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId InitialCharges } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['InitialCharges'] == None, rv_data

    def test_initial_magmom_sproperty(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId InitialMagmoms } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['InitialMagmoms'] == '[ 0.  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.\n  0.]', rv_data

    def test_pbc_sproperty(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId Pbc } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Pbc'] == '[True, True, True]', rv_data

    def test_cell_sproperty(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId Cell } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Cell'] == '[[5.96175869354, 0.0, 0.0], [2.98087934677, 5.163034479838, 0.0], [0.0, 0.0, 31.301633384387]]', rv_data

    def test_positions_sproperty(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId Positions } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Positions'] == '[[1.0616137722102194e-05, 1.00430434533884e-05, 11.997829572739208], [2.9808667726514777, 4.5044227636223694e-06, 11.997834568811298], [1.49044206705398, 2.5815063385957604, 11.997838654842296], [4.471321767989074, 2.5815186754290025, 11.99782671393662], [1.4904505244993935, 0.8605114997454405, 14.449299006975322], [4.471314559369811, 0.8605074109181713, 14.4493119968848], [2.980875560937021, 3.4420108959380986, 14.449308866590593], [5.961757027072016, 3.4420189051324397, 14.449297102230025], [-4.483034685198158e-06, 1.7210181370421362, 16.8523039699823], [2.9808834348220747, 1.7210143925544918, 16.852307976625248], [1.4904397636199378, 4.302526395841851, 16.852306775315245], [4.471321269220247, 4.302522230598007, 16.85229912711207], [-0.03628027904941261, -0.05829102066632311, 19.329837847258815], [3.012819028302268, -0.025529687587881517, 19.226533590440482], [1.5168413560108742, 2.6232655688289497, 19.340919951038273], [4.451264393456487, 2.590945454445438, 19.2295508630318], [0.8738825829127541, 1.1621072044721459, 21.101176889774322], [0.8679584479779054, 1.0380807857407832, 22.30254059936361], [1.3589593016170325, 1.807364331890099, 22.816141687235255]]', rv_data

    def test_numbers_sproperty(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId Numbers } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Numbers'] == '[47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47, 7, 7, 1]', rv_data

    def test_equation_property(self):
        rv_data = self.get_data('{reactions(first: 1, reactants:"~H", distinct: false) { totalCount edges { node { id Equation } } }}')
        assert assert rv['data']['reactions']['edges'][0]['node']['Equation'] == 'CH2O* + * -> CHO* + H*', rv_data

if __name__ == '__main__':
    unittest.main()
