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
        assert len(rv_data['data']['systems']['edges']) == 3347, "Found " + str(len(rv_data['data']['systems']['edges'])) + " systems instead of 3347"

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

        assert results[0]['node']['doi'] == '10.1021/jacs.7b02622', results[0]['node']['doi']
        assert results[0]['node']['journal']  == 'JACS', results[0]['node']['journal']
        results_reactions = results[0]['node']['reactions']
        assert results_reactions[0]['dftCode'] == 'VASP_5.4.1', results_reactions[0]['dftCode']
        assert results_reactions[0]['dftFunctional'] == 'PBE+U=3.32', results_reactions[0]['dftFunctional']

    def test_order_key(self):
        query ='{systems(last: 1, order: "energy") {edges {node { Formula energy} } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['systems']['edges'][0]['node']['Formula'] == 'H', rv_data

    def test_order_key_descending(self):
        query ='{systems(last: 1, order: "-energy") {edges {node { Formula energy} } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['systems']['edges'][0]['node']['Formula'] == 'Cu36Zn3', rv_data

    def test_total_count(self):
        query ='{systems(first: 0) { totalCount edges { node { id } } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['systems']['totalCount'] == 3347, rv_data

    def test_resolve_publication_systems(self):
        query ='{publications(year: 2017, last: 1, before: "YXJyYXljb25uZWN0aW9uOjM=") { totalCount edges {node { systems { uniqueId } } } }}'
        rv_data = self.get_data(query)
        print(len(rv_data['data']['publications']['edges'][0]['node']['systems']))
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
        assert rv_data['data']['reactions']['totalCount'] == 128, rv_data

    def test_distinct_filter_off(self):
        query = '{reactions(first: 0, reactants:"~H", distinct: false) { totalCount edges { node { id } } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['reactions']['totalCount'] == 3307, rv_data

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
        assert rv_data['data']['systems']['totalCount'] == 3295, rv_data

    def test_operation_lt(self):
        query = '{systems(natoms:70, op:"lt" first: 3) { totalCount edges { node { id natoms Formula } } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['systems']['totalCount'] == 3293, rv_data

    def test_operation_ne(self):
        query = '{systems(natoms:70, op:"ne" first: 3) { totalCount edges { node { id natoms Formula } } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['systems']['totalCount'] == 3345, rv_data

    def test_reactants_expansion(self):
        query = '{reactions(first:0, reactants: "CO") { totalCount edges { node { id } } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['reactions']['totalCount'] == 438, rv_data
        
    def test_reactants_star(self):
        query = '{reactions(first:0, reactants: "COstar") { totalCount edges { node { id } } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['reactions']['totalCount'] == 21, rv_data

    def test_products_star(self):
        query = '{reactions(first:0, products: "COstar") { totalCount edges { node { id } } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['reactions']['totalCount'] == 772, rv_data

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
        rv_data = self.get_data('{systems(uniqueId: "607a860f01f8c9efe82d41e14d0f564c") { edges { node { uniqueId Facet } } }}')
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
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId charges } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['charges'] == None, rv_data

    def test_magmoms_property(self):
        rv_data = self.get_data('{systems(uniqueId: "704635cfa5b954b4fd69a61b82cd1041") { edges { node { uniqueId magmoms } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['magmoms'] == '[4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 0.0, 0.0]', rv_data

    def test_stress_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId stress } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['stress'] == None, rv_data

    def test_dipole_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId dipole } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['dipole'] == None, rv_data

    def test_forces_property(self):
        rv_data = self.get_data('{systems(uniqueId: "2baa0dff53f6e374ec62a851f1519203") { edges { node { uniqueId forces } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['forces'] == "[[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [-0.00614427004948372, 0.00449696949293127, -0.00986315727173091], [0.00879477058939808, 0.00917989376165844, 0.0352720011056403], [-0.00206053074046705, -0.0276901353694061, 0.0379683393499177], [0.0245038028154277, 0.0144735534975378, 0.017733582986786], [-0.00910656443668941, -0.00789937561938611, 0.014741863883181], [0.015184343620972, 0.00329439236786369, -0.0317452457101462]]", rv_data

    def test_momenta_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId momenta } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['momenta'] == None, rv_data

    def test_tags_property(self):
        rv_data = self.get_data('{systems(uniqueId: "2baa0dff53f6e374ec62a851f1519203") { edges { node { uniqueId tags } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['tags'] == "[7, 7, 7, 7, 6, 6, 6, 6, 5, 5, 5, 5, 3, 3, 3, 1, 0, 0]", rv_data

    def test_masses_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId masses } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['masses'] == None, rv_data

    def test_initial_charges_property(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId initialCharges } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['initialCharges'] == None, rv_data

    def test_initial_magmom_sproperty(self):
        rv_data = self.get_data('{systems(uniqueId: "607a860f01f8c9efe82d41e14d0f564c") { edges { node { uniqueId initialMagmoms } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['initialMagmoms'] == "[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]", rv_data

    def test_pbc_sproperty(self):
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId Pbc } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Pbc'] == '[True, True, True]', rv_data

    def test_cell_sproperty(self):
        rv_data = self.get_data('{systems(uniqueId: "607a860f01f8c9efe82d41e14d0f564c") { edges { node { uniqueId cell } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['cell'] == "[[5.977315042726, 0.0, 0.0], [2.988657521363, 5.176506673424, 0.0], [0.0, 0.0, 31.320685943271]]", rv_data

    def test_positions_sproperty(self):
        rv_data = self.get_data('{systems(uniqueId: "1c8b50a73d22bfd72b8b799a12b774fc") { edges { node { uniqueId positions } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['positions'] == "[[10.0, 10.763239, 10.5925363270631], [10.0, 11.5248997266606, 10.0018863364684], [10.0, 10.0015782733394, 10.0018863364684]]", rv_data

    def test_numbers_sproperty(self):
        rv_data = self.get_data('{systems(uniqueId: "1c8b50a73d22bfd72b8b799a12b774fc") { edges { node { uniqueId numbers } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['numbers'] == "[8, 1, 1]", rv_data

    def test_equation_property(self):
        rv_data = self.get_data('{reactions(first: 1, reactants:"~H", distinct: false) { totalCount edges { node { id Equation } } }}')
        assert rv_data['data']['reactions']['edges'][0]['node']['Equation'] == 'CH2O* + * -> CHO* + H*', rv_data

    def test_equation_property_gas(self):
        rv_data = self.get_data('{reactions(first: 1, reactants:"~Ogas", distinct: false) { totalCount edges { node { id Equation } } }}')
        assert rv_data['data']['reactions']['edges'][0]['node']['Equation'] == 'H2O(g) -> hfH2(g) + OH*', rv_data

    def test_timestamp_mtime(self):
        rv_data = self.get_data('{systems(first:10, order:"mtime") { edges { node { id Mtime } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Mtime'] == "Wed May  9 17:53:11 2018", rv_data

    def test_timestamp_ctime(self):
        rv_data = self.get_data('{systems(first:10, order:"ctime") { edges { node { id Ctime } } }}')
        assert rv_data['data']['systems']['edges'][0]['node']['Ctime'] == 'Fri Feb  2 07:09:45 2018', rv_data

    def test_page_info(self):
        rv_data = self.get_data('{systems(first: 2, after:"") { totalCount pageInfo { hasNextPage hasPreviousPage startCursor endCursor } edges { node { Formula energy mtime } } }}')
        assert rv_data['data']['systems']['pageInfo']['startCursor'] == 'YXJyYXljb25uZWN0aW9uOjA=', rv_data

    def test_keyvalue_state(self):
        rv_data = self.get_data('{systems(keyValuePairs: "state->gas") { totalCount edges { node { id } } }}')
        assert rv_data['data']['systems']['totalCount'] == 48, rv_data


if __name__ == '__main__':
    unittest.main()
