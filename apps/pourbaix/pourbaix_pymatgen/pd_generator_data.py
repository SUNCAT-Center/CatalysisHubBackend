from pymatgen.analysis.pourbaix.analyzer import PourbaixAnalyzer
from pymatgen.analysis.pourbaix.maker import PourbaixDiagram
from pymatgen.analysis.pourbaix.maker import PREFAC
from pymatgen.analysis.pourbaix.entry import MultiEntry
# from pymatgen.util.string import latexify
from pymatgen.util.coord import in_coord_list
from .pourdiag import pd_entries

import collections
import numpy as np
# import re

# def latexify_ion(formula):

#     return re.sub(r"()\[([^)]*)\]", r"\1$^{\2}$", formula)

# def print_name(element1,element2,mat_co_1,entry):
#     """
#     Print entry name if single, else print multientry
#     """
#     str_name = ""
#     entries= pd_entries(element1,element2)
#     pourbaix = PourbaixDiagram(entries, {element1: mat_co_1, element2: 1- mat_co_1})
#     pd = pourbaix
#     if isinstance(entry, MultiEntry):
#         if len(entry.entrylist) > 2:
#             return str(pd.qhull_entries.index(entry))
#         for e in entry.entrylist:
#             str_name += latexify_ion(latexify(e.name)) + " + "
#         str_name = str_name[:-3]
#         return str_name
#     else:
#         return latexify_ion(latexify(entry.name))
def print_name(element1,element2,mat_co_1,entry):
    """
    Print entry name if single, else print multientry
    """
    str_name = ""
    entries= pd_entries(element1,element2)
    pourbaix = PourbaixDiagram(entries, {element1: mat_co_1, element2: 1- mat_co_1})
    pd = pourbaix
    if isinstance(entry, MultiEntry):
        if len(entry.entrylist) > 2:
            return str(pd.qhull_entries.index(entry))
        for e in entry.entrylist:
            str_name += (e.name) + " + "
        str_name = str_name[:-3]
        return str_name
    else:
        return entry.name

def pourbaix_plot_data(element1,element2,mat_co_1,limits=None):
    """
    Get stable/unstable species required to plot Pourbaix diagram.

    Args:
        limits: 2D list containing limits of the Pourbaix diagram
            of the form [[xlo, xhi], [ylo, yhi]]

    Returns:
        stable_entries, unstable_entries
        stable_entries: dict of lines. The keys are Pourbaix Entries, and
        lines are in the form of a list
        unstable_entries: list of unstable entries
    """
    entries= pd_entries(element1,element2)
    pourbaix = PourbaixDiagram(entries, {element1: mat_co_1, element2: 1- mat_co_1})
    pd = pourbaix
    analyzer = PourbaixAnalyzer(pd)
#     self._analyzer = analyzer
    if limits:
        analyzer.chempot_limits = limits
    chempot_ranges = analyzer.get_chempot_range_map(limits)
#     self.chempot_ranges = chempot_ranges
    stable_entries_list = collections.defaultdict(list)

    for entry in chempot_ranges:
        for line in chempot_ranges[entry]:
            x = [line.coords[0][0], line.coords[1][0]]
            y = [line.coords[0][1], line.coords[1][1]]
            coords = [x, y]
            stable_entries_list[entry].append(coords)

    unstable_entries_list = [entry for entry in pd.all_entries
                             if entry not in pd.stable_entries]

    return stable_entries_list, unstable_entries_list

def pourbaix_data(element1,element2,mat_co_1,limits):
	"""
	Get data required to plot Pourbaix diagram.

    Args:
        limits: 2D list containing limits of the Pourbaix diagram
            of the form [[xlo, xhi], [ylo, yhi]]

    Returns:

	"""
   
	(stable_pb, unstable_pb) = pourbaix_plot_data(element1,element2,
	                                              mat_co_1,limits)

	if limits:
	    xlim = limits[0]
	    ylim = limits[1]
	else:
		analyzer = PourbaixAnalyzer(pd)
		xlim = analyzer.chempot_limits[0]
		ylim = analyzer.chempot_limits[1]

	# h_line[0]: x_axis: [pH_h_lmin, pH_h_max]
	# h_line[1]: y_axis: [U_h_lmin, U_h_max]    
	h_line = np.transpose([[xlim[0], -xlim[0] * PREFAC],
	                       [xlim[1], -xlim[1] * PREFAC]])
	o_line = np.transpose([[xlim[0], -xlim[0] * PREFAC + 1.23],
	                       [xlim[1], -xlim[1] * PREFAC + 1.23]])
	neutral_line = np.transpose([[7, ylim[0]], [7, ylim[1]]])
	V0_line = np.transpose([[xlim[0], 0], [xlim[1], 0]])

	labels_name = []
	labels_loc_x = []
	labels_loc_y = []	
	species_lines = []

	for entry, lines in stable_pb.items():
	    center_x = 0.0
	    center_y = 0.0
	    coords = []
	    count_center = 0.0
	    for line in lines:
	        (x,y) = line
	        species_lines.append(line)
	##        print(x,y)
	#         plt.plot(x,y,"k-",linewidth = 3)
	        for coord in np.array(line).T:  
	            if not in_coord_list(coords, coord):
	                coords.append(coord.tolist())
	                cx = coord[0]
	                cy = coord[1]
	                center_x += cx
	                center_y += cy
	                count_center += 1.0
	    if count_center == 0.0:
	        count_center = 1.0
	    center_x /= count_center
	    center_y /= count_center
	    if ((center_x <= xlim[0]) | (center_x >= xlim[1]) |
	            (center_y <= ylim[0]) | (center_y >= ylim[1])):
	        continue
	    # xy = (center_x, center_y)
	    labels_name.append(print_name(element1,element2,mat_co_1,entry))
	    # labels_name.append(entry)
	    labels_loc_x.append(center_x)
	    labels_loc_y.append(center_y)

	return labels_name,labels_loc_x,labels_loc_y,species_lines,h_line, o_line, neutral_line, V0_line







