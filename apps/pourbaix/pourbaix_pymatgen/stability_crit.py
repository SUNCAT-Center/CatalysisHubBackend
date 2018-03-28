from .pd_screen_tools import ORR_line
from pymatgen.analysis.pourbaix.maker import PREFAC
import numpy as np


def most_stable_phase(phase_regions, scale='RHE'):
    """Returns a list containing how close the closest phase is to the ORR
    equilbrium line and the Pourbaix entry object(s) corrsponding to that phase

    Meant to be used with phase_filter to create the input to this method

    Parameters:
    -----------
    phase_regions: (unknown)
        PD regions which will be analyzed
        Pt_ref = True, difference between the Pt V_crit and system's V_crit
    scale: str
        RHE = V_crit on an RHE scale
    """
    point_dis_ORR_lst = []
    cnt = 0
    for region in phase_regions:
        dist_ORR_reg_lst = []  # Distance from ORR for all sides of region
        for line in region[0]:
            dist_ORR_0 = ORR_line(line[0][0]) - line[1][0]  # Distance from ORR
            # for 1st endpoint
            dist_ORR_1 = ORR_line(line[0][1]) - line[1][1]  # Distance from ORR
            # for 2nd endpoint
            # Grabs closest point from line segment
            dist_ORR_reg_lst.append(min(dist_ORR_0, dist_ORR_1))
        # Closest point on closest side to ORR line for phase region
        min_dist_ORR = min(dist_ORR_reg_lst)

        point_dis_ORR_lst.append([])
        point_dis_ORR_lst[cnt].append(min_dist_ORR)  # Closeness to ORR
        point_dis_ORR_lst[cnt].append(region[1])  # Pourbaix entry object

        cnt = cnt + 1
    most_stable_reg = min(point_dis_ORR_lst)  # Closest point to ORR for

    if scale == 'ORR_dist':
        most_stable_reg = most_stable_reg

    elif scale == 'Pt_ref':
        Pt_diss_V = 0.6470339

        most_stable_reg[0] = 1.23 - most_stable_reg[0] - Pt_diss_V

    elif scale == 'RHE':
        most_stable_reg[0] = 1.23 - most_stable_reg[0]

    return most_stable_reg


def oxidation_dissolution_product(phase_regions_all, most_stable_phase):
    """Returns the Pourbaix Entry of the most likely dissolved or oxidized phase
    given a starting stable phase

    Graphically, this is the phase which is above the stable phase (In terms of
    voltage), near the pH region at which stable phasae has the highest V_crit
    """
    slope = -0.0591

    phase_regions_all_copy = phase_regions_all[:]

    for region in phase_regions_all_copy:
        if region[1] == most_stable_phase[1]:
            stable_region_coord_tmp = region

    stable_region_coord = stable_region_coord_tmp[0]

    # Converting the coordinates to a RHE scale
    for side in stable_region_coord:
        side[1][0] = side[1][0] - slope * side[0][0]
        side[1][1] = side[1][1] - slope * side[0][1]

    # Finding the highest Voltage in the stable phase vs RHE
    highest_V = -20
    for side in stable_region_coord:
        if side[1][0] >= highest_V:
            highest_V = side[1][0]

        if side[1][1] >= highest_V:
            highest_V = side[1][1]

    # Returns the coordinate of the most stable side/point
    highest_V_points = []
    for side in stable_region_coord:
        if round(side[1][0], 4) == round(highest_V, 4):
            highest_V_points.append([side[0][0], side[1][0]])

        if round(side[1][1], 4) == round(highest_V, 4):
            highest_V_points.append([side[0][1], side[1][1]])

    lst_0 = np.round(highest_V_points, 6)
    set_1 = set(map(tuple, lst_0))
    most_stable_points = list(map(list, set_1))

    for point in most_stable_points:
        point[1] = point[1] - PREFAC * point[0]

    # Reversing the coordinates to a SHE scale
    for side in stable_region_coord:

        side[1][0] = side[1][0] + slope * side[0][0]
        side[1][1] = side[1][1] + slope * side[0][1]

    def format_to_point_pairs(line_segment):

        point_0 = [line_segment[0][0], line_segment[1][0]]
        point_1 = [line_segment[0][1], line_segment[1][1]]

        return [point_0, point_1]

    def compare_points(point_0, point_1, rounding):
        if round(
                point_0[0],
                rounding) == round(
                point_1[0],
                rounding) and round(
                point_0[1],
                rounding) == round(
                    point_1[1],
                rounding):
            return True

    adj_reg_lst = []
    for point in most_stable_points:

        for region in phase_regions_all:

            if region == stable_region_coord_tmp:
                continue

            for segment in region[0]:

                point_0 = format_to_point_pairs(segment)[0]
                point_1 = format_to_point_pairs(segment)[1]

                if compare_points(
                        point_0,
                        point,
                        3) or compare_points(
                        point_1,
                        point,
                        4):
                    adj_reg_lst.append(region)

    def make_unique(original_list):
        unique_list = []
        [unique_list.append(obj)
         for obj in original_list if obj not in unique_list]
        return unique_list

    def binary_region_entries(region):
        if len(i[1]) == 1:
            return [i[1][0]]
        if len(i[1]) == 2:
            return [i[1][0], i[1][1]]

    uniq_lst = make_unique(adj_reg_lst)

    for i in uniq_lst:
        i.append(adj_reg_lst.count(i))
    tmp = max(uniq_lst, key=lambda x: x[2])

    neighbor_reg_0 = binary_region_entries(tmp)

    name_lst = []
    for i in neighbor_reg_0:
        name_lst.append(i.phase_type)

    return name_lst


def is_nonox_phase(phase_regions):
    """Checks if there exits a non-oxide solid phase
    "Position-agnositic" stability criteria on a Pourbaix Diagram

    Parameters:
    -----------
    phase_regions:
        PD regions which will be analyzed
    """
    non_oxide = False
    for region in phase_regions:
        if len(region[1]) == 1:		# region has one entry
            if not region[1][0].phase_type == 'Solid':
                break  # Region solid?
            for elem in region[1][0].composition.elements:
                if elem.symbol == 'O':
                    break

        elif len(region[1]) == 2:		# region has two entries
            reg_phase_type_1 = region[1][0].phase_type
            reg_phase_type_2 = region[1][1].phase_type
            if not reg_phase_type_1 == 'Solid' and reg_phase_type_2 == 'Solid':
                break
            elem_lst = []
            elem_comb = region[1][0].composition.elements + \
                region[1][1].composition.elements
            for elem in elem_comb:
                elem_lst.append(elem.symbol)
            if 'O' not in elem_lst:
                non_oxide = True
                break

    return non_oxide
