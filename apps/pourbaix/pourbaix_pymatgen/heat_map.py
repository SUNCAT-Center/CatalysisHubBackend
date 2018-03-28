from .pourdiag import pd_entries
from .entry_methods import alloy_entries, base_atom
from .pd_screen_tools import phase_coord, phase_filter
from .stability_crit import most_stable_phase
from .stability_crit import oxidation_dissolution_product
import numpy as np
import matplotlib.colors as colors
import matplotlib.pyplot as plt
import matplotlib.patheffects as PathEffects
from .element_list import elem_str_mke
import fnmatch
import os


def process(i, j, comp=0.5, heat_map_scale='Pt_ref'):
    """Creates and analyzes a Pourbaix Diagram from two elements (they can be the
    same ex. Pt,Pt). Finds relevant entries, creates Pourbaix diagram,
    identifies stable phases, and calculates the stability of the phase

    Parameters:
    -----------
    i: object?
        First element in the system
    j: object?
        Second element in the system
    comp: float
        Composition loading of the two elements
    """
    entries = pd_entries(i.symbol, j.symbol)

    coord = phase_coord(entries, comp, prim_elem=i.symbol)
    filt1 = phase_filter(coord, 'metallic')
    filt2 = phase_filter(coord, 'metallic_metallic')
    filt = filt1 + filt2

    if not filt:
        print('heat_map.process - no phase present - ' + i.symbol + '-' + j.symbol)
        msp = [-1.5, 'Pourbaix Entry placeholder']
    else:
        msp = most_stable_phase(filt, scale=heat_map_scale)

    return msp


def process_alloy(i, j):
    """Creates and analyzes a Pourbaix Diagram from two elements (they can be the
    same ex. Pt,Pt). Finds relevant entries, removes the pure element entries,
    for each alloy removes all other alloys and analyzes stability of all
    forced alloy phases. Returns the the most highest performing forced alloy
    phase.

    Parameters:
    -----------
    i: object?
        First element in the system
    j: object?
        Second element in the system
    """
    entries = pd_entries(i.symbol, j.symbol)
    alloy_entr = alloy_entries(entries)
    if not alloy_entr:
        print('heat map - no alloy entries')
        non_alloy = process(i, j)
        return non_alloy

    base_atoms = base_atom(entries)
    alloy_performance_lst = []
    for alloy in alloy_entr:
        entries_0 = entries[:]
        comp = alloy.composition \
            .fractional_composition.get_atomic_fraction(base_atoms[0])
        for alloy_0 in alloy_entr:
            if not alloy_0 == alloy:
                entries_0.remove(alloy_0)

        coord = phase_coord(entries_0, comp)
        filt1 = phase_filter(coord, 'metallic')
        filt2 = phase_filter(coord, 'metallic_metallic')
        filt = filt1 + filt2
        try:
            alloy_performance_lst.append(
                most_stable_phase(filt, scale='Pr_ref'))
        except BaseException:
            pass

    alloy_performance_lst.sort(key=lambda x: x[0], reverse=True)
    # NOTE This sort will not work when the performance criteria is distance
    # from the ORR line (which needs to be as small as possible)

    try:
        best_alloy = alloy_performance_lst[0]
    except BaseException:
        best_alloy = [-1, 'placeholder']  # TODO: Make this better
    return best_alloy


def construct_output_matrix(elem):
    """ Constructs the skeleton of the output matrix from the element sweep. Matrix
    is square with dimensions of n, where n is the number of elements in elem

    Parameters:
    -----------
    elem: list
        elements to be screened over.
    """
    o_lst = []
    i_cnt = 0
    for i in elem:
        o_lst.append([])
        for j in elem:
            o_lst[i_cnt].append([])
        i_cnt = i_cnt + 1

    return o_lst


def finish_symmetric_matrix(elem, output_lst):
    """Fills in the the opposite diagonal of a symmetric matrix

    Parameters:
    -----------
    elem: list
        elements to be screened over.
    output_lst: ndarray?
        Half filled matrix to be filled in.
    """
    i_cnt = 0
    for i in elem[:-1]:
        j_cnt = 1
        for j in elem[1:]:
            output_lst[i_cnt][j_cnt] = output_lst[j_cnt][i_cnt]
            j_cnt = j_cnt + 1
        i_cnt = i_cnt + 1

    return output_lst


def run_all_binary_combinations(elements, loop_funct, scale):
    o_lst = construct_output_matrix(elements)

    print('constructing output V_crit matrix from scratch')

    i_cnt = 0
    for j in elements:
        for i in elements[i_cnt:]:
            print('##_' + j.symbol + i.symbol + '_##')
            output = loop_funct(i, j, scale)
            o_lst[elements.index(i)][elements.index(j)] = output

            print('_')
        print('_________________________________________')
        i_cnt = i_cnt + 1
    print('#########################################')

    o_lst = finish_symmetric_matrix(elements, o_lst)

    return o_lst


def calc_crit_V(i, j, scale):

    entry_processed = process(i, j, heat_map_scale=scale)

    return entry_processed


def oxidation_dissolution_product_0(i, j, scale):
    """Creates Pourbaix Diagrams for single or binary systems"""
    elem0 = i.symbol
    elem1 = j.symbol

    # Composition of 1st entry in elem_sys
    mat_co_0 = 0.50

    entr = pd_entries(elem0, elem1)

    coord = phase_coord(entr, mat_co_0)
    filt1 = phase_filter(coord, 'metallic')
    filt2 = phase_filter(coord, 'metallic_metallic')
    filt = filt1 + filt2
    msp = most_stable_phase(filt, scale='RHE')

    tmp = oxidation_dissolution_product(coord, msp)

    if 'Ion' in tmp:
        entry_lst = 'dis'
    else:
        entry_lst = 'oxi'

    return entry_lst


def ref_atoms(i, j, scale):
    """ """
    ref_atoms = pd_entries(i.symbol, j.symbol)
    print(ref_atoms)

    return ref_atoms


class MidpointNormalize(colors.Normalize):
    """ Used with diverging color schemes to set the white color to 0"""
    def __init__(self, vmin=None, vmax=None, midpoint=None, clip=False):
        self.midpoint = midpoint
        colors.Normalize.__init__(self, vmin, vmax, clip)

    def __call__(self, value, clip=None):
        # I'm ignoring masked values and all kinds of edge cases to make a
        # simple example...
        x, y = [self.vmin, self.midpoint, self.vmax], [0, 0.5, 1]
        return np.ma.masked_array(np.interp(value, x, y))


def extract_data_from_matrix(output_lst):
    """Extracts numerical data from screen output matrix (because the output
    matrix entries contain numerical stability and PD entry data) and makes a
    completley numerical matrix for plotting

    Parameters:
    -----------
    output_lst: list
        Matrix containing numerical data paired with entry data
    """
    data_matrix = []
    cnt = 0
    for i in output_lst:
        data_matrix.append([])
        for j in i:
            try:
                data_matrix[cnt].append(j[0])
            except BaseException:
                data_matrix[cnt].append(0)
        cnt = cnt + 1

    return data_matrix


def plot_heat_map(
        data_matrix,
        elem,
        text_overlay=False,
        composition=False,
        show_plot=False,
        save_file=True,
        file_type='.pdf',
        heat_map_scale='Pt_ref'
):
    """Constructs heat map plot from a matrix. If another matrix is passed to
    text_overlay it will be overlayed as text on top of the heatmap squares

    Parameters:
    data_matrix: ndarray?
    elem: object?
    text_overlay: bool
        Matrix of data which will be overlayed on the heatmap, if
        =data_value it will overlay the numerical value for each grid point
    """
    fig, ax1 = plt.subplots(1, 1)
    if heat_map_scale == 'Pt_ref':
        cmap_ = 'seismic'
        img = ax1.imshow(	data_matrix, cmap=cmap_, interpolation='nearest',
                          norm=MidpointNormalize(midpoint=0.))

    elif heat_map_scale == 'RHE':
        cmap_ = 'seismic'
        img = ax1.imshow(	data_matrix, cmap=cmap_, interpolation='nearest',
                          norm=MidpointNormalize(midpoint=0.))

    elem_str = elem_str_mke(elem)
    ax1.tick_params(labelbottom='off', labeltop='on')
    plt.setp(ax1.get_xticklabels(), fontsize=28)
    plt.setp(ax1.get_yticklabels(), fontsize=28)
    tcks = list(range(0, len(elem_str)))
    plt.xticks(tcks, elem_str)
    plt.yticks(tcks, elem_str)
    plt.title(
        'Transition Metal Oxidation/Dissolution Stability Heat Map',
        y=1.06,
        fontsize=25. /
        23 *
        len(elem) +
        13
    )

    cb = plt.colorbar(img, spacing='uniform', fraction=0.046, pad=0.04)
    cb.ax.tick_params(labelsize=20. / 23 * len(elem) + 5)

    # Setting the colorbar label
    if heat_map_scale == 'Pt_ref':
        col_bar_lb = 'V_critical - V_Pt [V vs RHE]'
    elif heat_map_scale == 'RHE':
        col_bar_lb = 'V_critical [V vs RHE]'

    cb.set_label(
        col_bar_lb,
        rotation=-
        90,
        fontsize=25. /
        23 *
        len(elem) +
        10,
        labelpad=50
    )

    scl = 20. / 23. * len(elem) + 2
    fig.set_figheight(scl)
    fig.set_figwidth(scl)

    if composition:
        # Adding text to plot
        plt.text(
            0.1,
            0.9,
            str(composition),
            fontsize=45,
            ha='center',
            va='center',
            transform=ax1.transAxes).set_path_effects([
                PathEffects.withStroke(
                    linewidth=2,
                    foreground='w'
                )
            ])

    if text_overlay == 'data_value':
        text_overlay = np.array(data_matrix)

        diff = 1.
        min_val = 0.
        rows = text_overlay.shape[0]
        cols = text_overlay.shape[1]

        col_array = np.arange(min_val, cols, diff)
        row_array = np.arange(min_val, rows, diff)
        x, y = np.meshgrid(col_array, row_array)

        print('_________________________________________')

        import matplotlib.patheffects as PathEffects
        for col_val, row_val in zip(x.flatten(), y.flatten()):
            c = np.round(text_overlay[int(row_val), int(col_val)], 2)
            fontsize_0 = 17
            ax1.text(col_val, row_val, c, fontsize=fontsize_0, va='center', ha='center').set_path_effects(
                [PathEffects.withStroke(linewidth=2, foreground='w')])

    elif text_overlay:
        text_overlay = np.array(text_overlay)

        diff = 1.
        min_val = 0.
        rows = text_overlay.shape[0]
        cols = text_overlay.shape[1]

        col_array = np.arange(min_val, cols, diff)
        row_array = np.arange(min_val, rows, diff)
        x, y = np.meshgrid(col_array, row_array)

        for col_val, row_val in zip(x.flatten(), y.flatten()):

            c = str(text_overlay[row_val.astype(int), col_val.astype(int)])
            fontsize_0 = 26 / 2

            ax1.text(col_val, row_val, c, fontsize=fontsize_0, va='center', ha='center').set_path_effects(
                [PathEffects.withStroke(linewidth=2, foreground='w')])

    num_fle = len(fnmatch.filter(os.listdir('.'), '*' + file_type))
    fle_nme = 'fig_heat_map' + '_' + str(num_fle) + file_type

    if save_file:
        print('saving ' + fle_nme)
        fig.savefig(fle_nme, format='svg', spi=1200)

    if show_plot:
        plt.show()
