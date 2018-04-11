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


    #def test_graphql5(self):
        ## TEST if we can query by DOI
        #query = '{publications(doi: "10.1021/acs.jpcc.6b03375") { edges { node { title systems { Formula } } } }}'
        #rv_data = self.get_data(query)
        #results = rv_data['data']['publications']['edges']
        #assert results[0]['node']['title'] == "Framework for Scalable Adsorbate-Adsorbate Interaction Models"
        #print(len(results[0]['node']['systems']))
        
        ## TEST if we can query parts of reactions DB for autocompletion
        #query = '{reactions(products: "~", reactants: "~NO", distinct: true) { edges { node { reactants products } } }}'
        #rv_data = self.get_data(query, )

        #assert len(rv_data['data']['reactions']['edges']) == 1
        #assert 'reactants' in rv_data['data']['reactions']['edges'][0]['node']
        #assert 'products' in rv_data['data']['reactions']['edges'][0]['node']

    #def test_graphql6(self):
        ## TEST if distinct switch makes the expected difference
        #query = '{reactions(last: 10, reactants: "~COH", products: "~", distinct: true) { edges { node { reactants } } }}'
        #rv_data = self.get_data(query, )
        #pprint.pprint(rv_data['data']['reactions']['edges'])
        #print(len(rv_data['data']['reactions']['edges']))
        #assert len(rv_data['data']['reactions']['edges']) == 7, len(rv_data['data']['reactions']['edges'])

        #query = '{reactions(last: 10, reactants: "~COH", products: "~") { edges { node { reactants } } }}'
        #rv_data = self.get_data(query, verbose=True)
        #assert len(rv_data['data']['reactions']['edges']) == 9, len(rv_data['data']['reactions']['edges'])


        #query = '{reactions (first: 0) { totalCount }}'
        #rv_data = self.get_data(query, verbose=True)
        #assert rv_data['data']['reactions']['totalCount'] == 541, "Sample db has 210 entries"

        ## CONTINUE HERE BY PUSHING THE RETURN STATEMENT DOWN
        ## AND SUCCESSIVELY ADD assertions

        #query = """{reactions ( last: 5, surfaceComposition: "~", facet: "~", reactants: "~", products: "~" ) {
                   #edges {
                     #node {
                       #id 
                       #DFTCode
                       #DFTFunctional
                       #reactants
                       #products
                       #pubId
                       ##Equation
                       ##aseIds
                       ##reactantIds
                       ##productIds
                       #facet
                       #chemicalComposition
                       #reactionEnergy
                       #activationEnergy
                       #surfaceComposition
                     #}
                   #}
                 #}}
                 #"""
        #rv_data = self.get_data(query, verbose=True)
        
        #query = """
                #{systems(uniqueId: """ + \
                #uniqueId + \
                #""") {
                           #edges {
                             #node {
                             #Formula
                             #energy
                             #Cifdata
                             #PublicationYear
                             #PublicationDoi
                             #PublicationAuthors
                             #PublicationTitle
                             #PublicationVolume
                             #PublicationUrl
                             #PublicationNumber
                             #PublicationJournal
                             #PublicationPages
                             #uniqueId
                             #volume
                             #mass
                             #}
                           #}
                         #}}
                #"""
        
        ##rv_data = self.get_data(query, verbose=True)

        ##query = ' {reactions(reactants: "~", distinct: true) { edges { node { reactants } } }} '
        ##rv_data = self.get_data(query, verbose=True)


        #query = ' {reactions(products: "~", distinct: true) { edges { node { products } } }} '
        #rv_data = self.get_data(query, verbose=True)

        #query = ' {reactions(surfaceComposition: "~", distinct: true) { edges { node { surfaceComposition } } }} '
        #rv_data = self.get_data(query, verbose=True)

        #query = ' {reactions(facet: "~", distinct: true) { edges { node { facet } } }} '
        #rv_data = self.get_data(query, verbose=True)

        #query = """{systems(uniqueId: "${uuid}") {
           #edges {
             #node {
             #Formula
             #energy
             #Cifdata
             #PublicationYear
             #PublicationDoi
             #PublicationAuthors
             #PublicationTitle
             #PublicationVolume
             #PublicationUrl
             #PublicationNumber
             #PublicationJournal
             #PublicationPages
             #DftCode
             #DftFunctional
             #}
           #}
         #}}"""
        ##rv_data = self.get_data(query, verbose=True)



        #query = '{systems(last: 10) { edges { node { PublicationYear } } }}'
        ##rv_data = self.get_data(query, verbose=True)

        #query = '{systems(last: 10) { edges { node { Formula } } }}'
        #rv_data = self.get_data(query, verbose=True)

        #query = ' {reactions { edges { node { id } } }} '
        #rv_data = self.get_data(query, verbose=True)


        #query = '{systems(last: 10) { edges { node { id } } }}'
        #rv_data = self.get_data(query, verbose=True)

        #query = ' {reactions { edges { node { doi } } }} '
        #rv_data = self.get_data(query, verbose=True)


    ##def test_root_website(self):
        ##rv = self.app.get('/')
        ##assert b'Welcome to the catalysis hub database!' in rv.data

if __name__ == '__main__':
    unittest.main()
