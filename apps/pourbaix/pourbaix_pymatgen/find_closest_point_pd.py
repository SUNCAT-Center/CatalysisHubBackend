from pymatgen.analysis.pourbaix.plotter import PourbaixPlotter
import matplotlib.pyplot as plt
import numpy as np
from pymatgen.analysis.pourbaix.maker import PREFAC
import sys


def screening_check_desirable(entry, criteria='only-solid'):
    """Ambar's Region Filter Check Function """
    is_desired = False
    if criteria not in ['only-solid']:
        print("Not implemented")
        sys.exit()
    if criteria == 'only-solid':
        if entry.nH2O == 0.0 and entry.npH == 0.0 and entry.nPhi == 0.0:
            is_desired = True
            print("Desired entry", entry.name)
    if not criteria:
        print("Not desired entry", entry.name)

    return is_desired


def get_water_stability_lines(limits):
    """Ambar's Function for Water and Hydrogen Lines """
    xlim = limits[0]
    h_line = np.transpose([[xlim[0], -xlim[0] * PREFAC],
                           [xlim[1], -xlim[1] * PREFAC]])
    o_line = np.transpose([[xlim[0], -xlim[0] * PREFAC + 1.23],
                           [xlim[1], -xlim[1] * PREFAC + 1.23]])

    return (h_line, o_line)


def find_closest_point_pd(pourbaix_diagram_object):
    """ """
    lw = 1
    limits = [[-2, 16], [-3, 3]]

    plotter = PourbaixPlotter(pourbaix_diagram_object)
    (stable, unstable) = plotter.pourbaix_plot_data(limits)

    # Returns the Desirable Regions of PD in "vertices"
    vertices = []

    for entry, lines in list(stable.items()):
        print(entry.name)
        is_desired = screening_check_desirable(entry, criteria='only-solid')
        if is_desired:
            desired_entry = entry
        for line in lines:
            (x, y) = line
            plt.plot(x, y, "k-", linewidth=lw)
            point1 = [x[0], y[0]]
            point2 = [x[1], y[1]]
            if point1 not in vertices and is_desired:
                vertices.append(point1)
            if point2 not in vertices and is_desired:
                vertices.append(point2)

    # Placing the desired phase's name in the diagram
    center_x = 0
    center_y = 0
    count = 0
    for point in vertices:
        x, y = point
        count = count + 1
        center_x = center_x + x
        center_y = center_y + y
        plt.plot(x, y, 'ro')
    center_x = center_x / count
    center_y = center_y / count
    plt.annotate(str(desired_entry.name), xy=(center_x, center_y))

    # Plotting Water and Hydrogen Equilibrium Lines. Get water line
    h_line, o_line = get_water_stability_lines(limits)
    plt.plot(h_line[0], h_line[1], "r--", linewidth=lw)
    plt.plot(o_line[0], o_line[1], "r--", linewidth=lw)

    # Getting distances
    print("Getting distances of vertices")
    reference_line = o_line
    p1 = np.array([reference_line[0][0], reference_line[1][0]])
    p2 = np.array([reference_line[0][1], reference_line[1][1]])

    min_d = 1000.0
    d_and_vert_lst = []
    for p3 in vertices:
        np.array(p3)
        d = np.linalg.norm(np.cross(p2 - p1, p1 - p3)) / \
            np.linalg.norm(p2 - p1)
        d_and_vert = [d, p3]
        d_and_vert_lst.append(d_and_vert)

        # https://stackoverflow.com/questions/39840030/distance-between-point-and-a-line-from-two-points
        # http://www.fundza.com/vectors/point2line/index.html
        print("Vertex: ", p3, "Distance: ", d)

        if d <= min_d:
            min_d = d

    fin_lst = []
    for i in d_and_vert_lst:
        if round(i[0], 4) == round(min_d, 4):
            fin_lst.append(i)

    # Plotting the star on highest stability vertices
    for i in fin_lst:
        plt.plot(i[1][0], i[1][1], '*b', ms=16)

    ###########################################
    V_RHE = 1.23 - min_d

    pH_0 = fin_lst[0][1][0]
    V_SHE = V_RHE - PREFAC * pH_0
    ###########################################

    # plt.annotate('d = '+ str(round(min_d,2)),xy=(center_x, center_y-0.3))
    plt.annotate('V_crit = ' + str(round(V_RHE, 2)) +
                 ' VvsRHE', xy=(center_x, center_y - 0.3))
    plt.annotate('V_crit = ' + str(round(V_SHE, 2)) +
                 ' VvsSHE', xy=(center_x, center_y - 0.6))
    plt.xlabel("pH")
    plt.ylabel("E (V)")
    plt.show()
