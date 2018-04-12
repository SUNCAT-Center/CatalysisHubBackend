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
        assert len(['data']['publications']['edges'][0]['node']['systems']) == 7, rv_data

    def test_resolve_input_file(self):
        query ='{systems(last: 1, order: "-energy") {edges {node { Formula energy InputFile(format: "vasp")} } }}'
        rv_data = self.get_data(query)
        assert rv_data['data']['systems']['edges'][0]['node']['InputFile'].strip() == """
        Zn Cu \n 1.0000000000000000\n     6.3679644736317025    0.0000000000000000    0.0000000000000000\n     0.0000000000000000    7.7979735829252466    0.0000000000000000\n     0.0000000000000000    0.0000000000000000   22.1434721200745948\n   3  36\nCartesian\n  2.0855219452025864  1.3070737659269522 10.1548117902441373\n  2.0891600935455132  3.9085296800250684 10.1525043441014411\n  2.0801526600884226  6.5083006783221808 10.1560195692017832\n -0.0203349384613197  0.0056618535710029  9.3962849887213959\n -0.0117113220492381  2.6049981055720588  9.3944038945974864\n -0.0150206598835190  5.2035729767478385  9.3945199126941308\n  4.2646813722219790  1.3040490017575379  8.6930707303076211\n  4.2678819843053004  3.9004547864086065  8.6898344449336040\n  4.2619114823548401  6.4989556109805120  8.6954659287061364\n  2.1652367862454835  0.0041743521358172  7.8640969647589447\n  2.1657388992120574  2.6028313491549753  7.8661266223903672\n  2.1652106232349482  5.2037950572892768  7.8659362436443097\n  0.0126066804075260  1.3026313626384285  7.1619963016208832\n  0.0135266878664242  3.9014168428362961  7.1602442982432519\n  0.0117920207015753  6.5009295750080280  7.1628355355273916\n  4.2622189198710227  0.0002444499020848  6.4028744861505205\n  4.2602614614781507  2.5994583727219029  6.4008233440759907\n  4.2609502041749456  5.1995136276718057  6.4018952130206301\n  2.1269861186218306  1.3013457048445443  5.6351321600071058\n  2.1274380160882598  3.9006414494207227  5.6369868543907673\n  2.1268640167827746  6.4993711936344791  5.6350189230494268\n  0.0000000000000000  0.0000000000000000  4.9076316409619754\n  0.0000000000000000  2.5993245016485034  4.9076316409619754\n  0.0000000000000000  5.1986490812767432  4.9076316409619754\n  4.2453096703143496  1.2996622898141197  4.1571598314208389\n  4.2453096703143496  3.8989867914626233  4.1571598314208389\n  4.2453096703143496  6.4983112931111267  4.1571598314208389\n  2.1226548033173525  0.0000000000000000  3.4066880218797029\n  2.1226548033173525  2.5993245016485034  3.4066880218797029\n  2.1226548033173525  5.1986490812767432  3.4066880218797029\n  0.0000000000000000  1.2996622898141197  2.6562161901950945\n  0.0000000000000000  3.8989867914626233  2.6562161901950945\n  0.0000000000000000  6.4983112931111267  2.6562161901950945\n  4.2453096703143496  0.0000000000000000  1.9057443806539580\n  4.2453096703143496  2.5993245016485034  1.9057443806539580\n  4.2453096703143496  5.1986490812767432  1.9057443806539580\n  2.1226548033173525  1.2996622898141197  1.1552725711128218\n  2.1226548033173525  3.8989867914626233  1.1552725711128218\n  2.1226548033173525  6.4983112931111267  1.1552725711128218\n'
        """.strip(), rv_data

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
