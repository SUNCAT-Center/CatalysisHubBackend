
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


def connect_db():
    rv = sqlite3.connect(app.app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def get_db():
    if not(hasattr(flask.g, 'sqlite_db')):
        flask.g.sqlite_db = connect_db()
    return flask.g.sqlite_db


def init_db(app):
    db = get_db()
    with app.open_resource('tests/pg_sample_data.sql') as f:
        db.cursor().executescript(f.read().decode())
    db.commit()


class CatappBackendTestCase(unittest.TestCase):
    def setUp(self):
        TEST_DB_FILENAME = './test_database.db'
        self.db_fd = open(TEST_DB_FILENAME, 'w',)
        app.app.config['DATABASE'] = TEST_DB_FILENAME
        #self.db_fd, app.app.config['DATABASE'] = 'test_data'
        os.environ['SQLITE_DB'] = app.app.config['DATABASE']
        app.app.testing = True
        self.app = app.app.test_client()
        with app.app.app_context():
            init_db(app.app)

    def get_data(self, query, verbose=False):
        if verbose == True:
            print('\n\nQUERY {query}'.format(**locals()))
        data = json.loads(
            self.app.post('/graphql?query={query}'.format(**locals())).data
                )
        if verbose == True:
            print('DATA')
            pprint.pprint(data)
        return data


    def tearDown(self):
        #os.close(self.db_fd)
        self.db_fd.close()
        os.unlink(app.app.config['DATABASE'])


    def test_graphql(self):
        #rv = self.app.post('/graphql?query={systems(last: 10){no}}')
        # TEST that some systems are returned
        rv_data = self.get_data('{systems(last: 10) { edges { node { uniqueId } } }}')
        assert 'data' in rv_data
        assert 'systems' in rv_data['data']
        assert 'edges' in rv_data['data']['systems']
        assert len(rv_data['data']['systems']['edges']) == 10

        # test that the right number of systems is returned
        rv_data = self.get_data('{systems { edges { node { uniqueId } } }}')
        assert len(rv_data['data']['systems']['edges']) == 330

        # assert that unique id has 32 characters
        uniqueId = rv_data['data']['systems']['edges'][0]['node']['uniqueId']
        assert len(uniqueId) == 32

        rv_data = self.get_data("{systems(uniqueId: \"" + uniqueId + "\") { edges { node { Cifdata } } }}")
        pprint.pprint(rv_data)
        # TODO: Current CifData is None
        #       Analyze and consider fixing

        # TEST that 10 elements with energy are returned
        rv_data = self.get_data("{systems(last: 10 ) { edges { node { energy Cifdata } } }}")
        #pprint.pprint(rv_data)
        assert len(rv_data['data']['systems']['edges']) == 10
        for node in rv_data['data']['systems']['edges']:
            assert node['node']['energy'] < 10

        # TEST that querying for years, gives meaningful in publications
        query = '{numberKeys(last: 10, key:"publication_year") { edges { node { value } } }}'
        rv_data = self.get_data(query)

        # TEST if we can filter catapp reactions by yearko
        query = '{catapp(last: 10, year: 2017) { edges { node { year publication doi dftCode dftFunctional } } }}'
        rv_data = self.get_data(query)
        results = rv_data['data']['catapp']['edges']
        assert 'node' in results[0]
        assert 'dftCode' in results[0]['node']
        assert results[0]['node']['dftCode'] == 'VASP_5.4.1'
        assert 'dftFunctional' in results[0]['node']
        assert results[0]['node']['dftFunctional'] == 'PBE+U=3.32'

        assert 'publication' in results[0]['node']

        publication = (eval(results[0]['node']['publication']))
        assert publication['doi'] == '10.1021/jacs.7b02622'
        assert publication['journal'] == 'JACS'



        # TEST if we can query by DOI
        query = '{systems(keyValuePairs: "~doi\\": \\"10.1021/acs.jpcc.6b03375") { edges { node { natoms Formula Facet uniqueId energy DftCode DftFunctional PublicationTitle PublicationAuthors PublicationYear PublicationDoi } } }}'
        rv_data = self.get_data(query, verbose=True)
        results = rv_data['data']['systems']['edges']

        print(len(results))
        print(results[0])
        assert len(results) == 242

        # CONTINUE HERE BY PUSHING THE RETURN STATEMENT DOWN
        # AND SUCCESSIVELY ADD assertions
        return

        # TEST if we can query parts of catapp DB for autocompletion
        query = '{catapp(last: 10, products: "~COH", reactants: "~", distinct: true) { edges { node { reactants } } }}'
        rv_data = self.get_data(query, verbose=True)

        query = '{catapp(last: 10, reactants: "~COH", products: "~", distinct: true) { edges { node { reactants } } }}'
        rv_data = self.get_data(query, verbose=True)

        query = """{catapp ( last: 5, surfaceComposition: "~", facet: "~", reactants: "~", products: "~" ) {
                   edges {
                     node {
                       id DFTCode
                       DFTFunctional
                       reactants
                       products
                       #Equation
                       aseIds
                       #reactantIds
                       #productIds
                       facet
                       chemicalComposition
                       reactionEnergy
                       activationEnergy
                       surfaceComposition
                     }
                   }
                 }}
                 """
        rv_data = self.get_data(query, verbose=True)

        query = """
                {systems(uniqueId: """ + \
                uniqueId + \
                """) {
                           edges {
                             node {
                             Formula
                             energy
                             Cifdata
                             PublicationYear
                             PublicationDoi
                             PublicationAuthors
                             PublicationTitle
                             PublicationVolume
                             PublicationUrl
                             PublicationNumber
                             PublicationJournal
                             PublicationPages
                             uniqueId
                             volume
                             mass
                             }
                           }
                         }}
                """
        rv_data = self.get_data(query, verbose=True)

        query = ' {catapp(reactants: "~", distinct: true) { edges { node { reactants } } }} '
        rv_data = self.get_data(query, verbose=True)


        query = ' {catapp(products: "~", distinct: true) { edges { node { products } } }} '
        rv_data = self.get_data(query, verbose=True)

        query = ' {catapp(surfaceComposition: "~", distinct: true) { edges { node { surfaceComposition } } }} '
        rv_data = self.get_data(query, verbose=True)

        query = ' {catapp(facet: "~", distinct: true) { edges { node { facet } } }} '
        rv_data = self.get_data(query, verbose=True)

        query = """{systems(uniqueId: "${uuid}") {
           edges {
             node {
             Formula
             energy
             Cifdata
             PublicationYear
             PublicationDoi
             PublicationAuthors
             PublicationTitle
             PublicationVolume
             PublicationUrl
             PublicationNumber
             PublicationJournal
             PublicationPages
             DftCode
             DftFunctional
             }
           }
         }}"""
        rv_data = self.get_data(query, verbose=True)



        query = '{systems(last: 10) { edges { node { PublicationYear } } }}'
        rv_data = self.get_data(query, verbose=True)

        query = '{systems(last: 10) { edges { node { Formula } } }}'
        rv_data = self.get_data(query, verbose=True)

        query = ' {catapp { edges { node { id } } }} '
        rv_data = self.get_data(query, verbose=True)


        query = '{systems(last: 10) { edges { node { id } } }}'
        rv_data = self.get_data(query, verbose=True)

        query = ' {catapp { edges { node { doi } } }} '
        rv_data = self.get_data(query, verbose=True)





    #def test_root_website(self):
        #rv = self.app.get('/')
        #assert b'Welcome to the catapp database!' in rv.data

if __name__ == '__main__':
    unittest.main()
