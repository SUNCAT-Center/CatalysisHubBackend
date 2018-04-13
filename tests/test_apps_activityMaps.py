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


    def test_blank_reaction_query(self):
        data = json.loads(
                self.app.get('/apps/activityMaps/systems/?activityMap=blank')
                .data.decode('utf-8')
                )
        
        test_data = {'reference': '',
                        'systems': [],
                        'xlabel': '',
                        'ylabel': '',
                        'zlabel': ''}
        assert data == test_data, (data, test_data)


    #def test_NRR_reaction_query(self):
        #data = json.loads(
                #self.app.get('/apps/activityMaps/systems/?activityMap=NRR')
                #.data.decode('utf-8')
                #)
        
        #test_data = {'reference': '',
                        #'systems': [],
                        #'xlabel': '',
                        #'ylabel': '',
                        #'zlabel': ''}
        #assert data == test_data, (data, test_data)


    #def test_OER_reaction_query(self):
        #data = json.loads(
                #self.app.get('/apps/activityMaps/systems/?activityMap=OER')
                #.data.decode('utf-8')
                #)
        
        #test_data = {'reference': '',
                        #'systems': [],
                        #'xlabel': '',
                        #'ylabel': '',
                        #'zlabel': ''}
        #assert data == test_data, (data, test_data)


    #def test_ORR_reaction_query(self):
        #data = json.loads(
                #self.app.get('/apps/activityMaps/systems/?activityMap=ORR')
                #.data.decode('utf-8')
                #)
        
        #test_data = {'reference': '',
                        #'systems': [],
                        #'xlabel': '',
                        #'ylabel': '',
                        #'zlabel': ''}
        #assert data == test_data, (data, test_data)


    #def test_CO2RR_reaction_query(self):
        #data = json.loads(
                #self.app.get('/apps/activityMaps/systems/?activityMap=CO2RR')
                #.data.decode('utf-8')
                #)
        
        #test_data = {'reference': '',
                        #'systems': [],
                        #'xlabel': '',
                        #'ylabel': '',
                        #'zlabel': ''}
        #assert data == test_data, (data, test_data)


    #def test_CO_Hydro_reaction_query(self):
        #data = json.loads(
                #self.app.get('/apps/activityMaps/systems/?activityMap=CO_Hydrogenation_111')
                #.data.decode('utf-8')
                #)
        
        #test_data = {'reference': '',
                        #'systems': [],
                        #'xlabel': '',
                        #'ylabel': '',
                        #'zlabel': ''}
        #assert data == test_data, (data, test_data)
