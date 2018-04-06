'''Flask app for Pourbaix Diagrams'''
import io #StringIO

import urllib
import base64
#import mpld3
import numpy as np
#import plotly.plotly as py
#import plotly.tools as tls
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.image as image

from .pourbaix_ase.pourbaix_plot import solvated_ase,solid_Lange,Pourbaix
from matplotlib.backends.backend_agg import FigureCanvasAgg 
from .pourbaix_surface.pourbaix_plot import SurfPourbaix

import flask
from flask import Flask, jsonify,request 
from flask import Blueprint

#from pourbaix_pymatgen.pourdiag import pd_entries
from .pourbaix_pymatgen import pd_generator_data
#from pymatgen.analysis.pourbaix.maker import PourbaixDiagram
#from pymatgen.analysis.pourbaix.plotter import PourbaixPlotter
import sys

pourbaix = Blueprint('pourbaix', __name__)
@pourbaix.route('/', methods=['GET', 'POST'])

def get_spacies_ase():
    responses = []

    data = flask.request.get_json()
    
    element1 = str(data.get('element1'))     
    element2 = str(data.get('element2'))
    T = float(data.get('temperature'))
    checked_ase = data.get('checkedASE')
    checked_Lange = data.get('checkedLange')
    checked_ML = data.get('checkedML')
    
    ion_list_temp = []
    ion_list = []    
    solid_list = []
    if checked_ase == True and checked_Lange == False and checked_ML == False:
        ion_list_temp = solvated_ase(element1)+ solvated_ase(element2)
        ion_list = list(set(ion_list_temp))
        solid_list = solid_Lange(element1,T) + solid_Lange(element2,T)
    else:
        print ('ASE database is not checked!!')

    responses.append({
    "ion_list": ion_list,
    "solid_list":solid_list,
    })

    return jsonify(responses)


@pourbaix.route('/pourbaix_ase/', methods=['GET', 'POST'])
def pourbaix_gen_ase():

    responses = []

    data = request.get_json()

    element1 = str(data.get('element1'))     
    element2 =str(data.get('element2'))
    T = float(data.get('temperature'))
    checked_ase = data.get('checkedASE')
    checked_Lange = data.get('checkedLange')
    checked_ML = data.get('checkedML')

    ion_list = []    
    solid_list = []
    if checked_ase == True and checked_Lange == False and checked_ML == False:
        ion_list = solvated_ase(element1)+ solvated_ase(element2)
        solid_list = solid_Lange(element1,T) + solid_Lange(element2,T)
    else:
        print ('ASE database is not checked!!')

    elem1_compo = str(data.get('elem1_compo'))
    elem2_compo = str(data.get('elem2_compo'))

    ions_conc = {}
    ions_conc =data.get('ions_conc')


    overall_comp = (element1, elem1_compo, element2, elem2_compo, 'O', '1')
    refs = ion_list + solid_list

    pb = Pourbaix(refs,T, ions_conc, formula = ''.join(overall_comp))   
    U = np.linspace(-3, 3, 200)
    pH = np.linspace(-2, 14, 300)
    a, compositions, text, x_loc, y_loc, labels_text,fig = pb.diagram(U, pH, plot=True) #data_url
    
    fig = plt.gcf()
    canvas = FigureCanvasAgg(fig)
    a_list = a.tolist()
    output = io.BytesIO()
    canvas.print_png(output)
    output.seek(0)
    output_str = output.read()

    response = base64.b64encode(output_str).decode()
    data_url = 'data:image/jpeg;base64,{0}'.format(response)

    fig1 = plt.gcf().clear() #clean the catche for the previous fig

    responses.append({
        "data_url": data_url,
        "ions_conc":ions_conc,
        "figure_data": a_list,
        })

    return jsonify(responses)


@pourbaix.route('/pourbaix_pymatgen/', methods=['GET', 'POST'])
def pourbaix_gen_pymatgen():
    responses = []

    data = request.get_json()

    element1 = str(data.get('element1'))     
    element2 = str(data.get('element2'))
    mat_co_1 = float(data.get('mat_co_1'))

    if element2 is None:
        element2 = element1

    limits = [[-2, 14], [-3, 3]]

    labels_name,labels_loc_x,labels_loc_y,species_lines,h_line,\
    o_line, neutral_line, V0_line = pd_generator_data.pourbaix_data(element1,
                                                                    element2,
                                                                    mat_co_1,
                                                                    limits)  
    species_loc_x = []
    species_loc_y = []

    for line in species_lines:
        (x,y) = line
        species_loc_x.append(x)
        species_loc_y.append(y)

    h_line_x = list(h_line[0])   
    h_line_y = list(h_line[1])

    o_line_x = list(o_line[0])   
    o_line_y = list(o_line[1])

    neutral_line_x = list(neutral_line[0])   
    neutral_line_y = list(neutral_line[1])

    V0_line_x = list(V0_line[0])   
    V0_line_y = list(V0_line[1])

    responses.append({
        "labels_name":labels_name,
        "labels_loc_x" : labels_loc_x,
        "labels_loc_y" : labels_loc_y,
        "species_loc_x":species_loc_x,
        "species_loc_y":species_loc_y,
        "h_line_x": h_line_x,
        "h_line_y": h_line_y,
        "o_line_x": o_line_x,
        "o_line_y": o_line_y,
        "neutral_line_x": neutral_line_x,
        "neutral_line_y": neutral_line_y,
        "V0_line_x": V0_line_x,
        "V0_line_y": V0_line_y,
    })

    return jsonify(responses)



@pourbaix.route('/pourbaix_surface/', methods=['GET', 'POST'])
def pourbaix_gen_surface():
    responses = []

    surfs = [
    [ -541.29070522, 0,0,0],   # clean surface 
    [ -581.50171715, 0, 0, 4], # clean surface  + 4 OH adsorbates
    [ -559.21450110, 0, 4, 0], # clean surface  + 4 O adsorbates 
    ]

    SurfPourbaix(surfs).pourbaix_plotter()
    fig1 = plt.gcf()
    canvas = FigureCanvasAgg(fig1) 
    output = io.BytesIO()
    canvas.print_png(output)
    output.seek(0)
    output_str = output.read()
    response = base64.b64encode(output_str).decode()
    data_url = 'data:image/jpeg;base64,{0}'.format(response)
    fig1 = plt.gcf().clear() #clean the catche for the previous fig

    responses.append({
        "data_url": data_url,

        })

    return jsonify(responses)
   
