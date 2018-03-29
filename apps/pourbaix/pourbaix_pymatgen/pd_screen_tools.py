from .entry_methods import base_atom
from .pourdiag import pd_entries
from pymatgen.analysis.pourbaix.maker import PourbaixDiagram
from pymatgen.analysis.pourbaix.plotter import PourbaixPlotter
from pymatgen.analysis.pourbaix.entry import PourbaixEntry, MultiEntry
import matplotlib.pyplot as plt


def ORR_line(pH):
    intercept = 1.23
    slope = -0.0591

    V = slope * pH + intercept

    return V


def plot_reg(coord_data):
    """Plots the region boundaries for the given region

    Parameters:
    -----------
    coord_data:
        Coordinate data of region of interest, must be in the form
        of [[[x-points],[y-points]],[], ...]
    """
    fig, ax = plt.subplots()
    for line in coord_data:
        ax.plot(line[0], line[1])
    plt.show()


def phase_coord(entries, atom_comp, prim_elem=None):
    """Produces a list of line segments corresponding to each phase area in a PD
    along with the PD entries corresponding to each area.
    The produced list is of the following form:
        list = [[[coordinate data], [pourbaix entry]], [], [] .... ]

    Parameters:
    -----------
    entries: list
        entries in a PD
    atom_comp: float
        Composition of atom if system is binary, given as a fraction
        between 0 and 1. Corresponds to the element with lowest atomic
        number if prim_elem is left to its default
    prim_elem: str
        Primary element to which the atom_comp is assigned
    """
    base_atoms = base_atom(entries)
    mat0 = base_atoms[0]
    if len(base_atoms) == 2:
        mat1 = base_atoms[1]
    else:
        mat1 = mat0

    if prim_elem:
        for atom in base_atoms:
            if atom == prim_elem:
                mat0 = atom
            else:
                mat1 = atom

    pd = PourbaixDiagram(entries, {mat0: atom_comp, mat1: 1 - atom_comp})
    pl = PourbaixPlotter(pd)
    ppd = pl.pourbaix_plot_data([[-2, 16], [-3, 3]])

    pd_lst = []
    for i, stable_entry in enumerate(ppd[0]):
        pd_lst += [[]]
        pd_lst[i] += [ppd[0][stable_entry]]
        if isinstance(stable_entry, PourbaixEntry):
            pd_lst[i] += [stable_entry]
        else:
            pd_lst[i] += [stable_entry.entrylist]
    return pd_lst


def phase_filter(phase_coord, phase_type):
    """Returns a list of Pourbaix diagrams regions and corresponding species
    that match the specified phase_type

    Parameters:
    -----------
    phase_coord: list
        PD phase coordinate data produced from phase_coord
    phase_type: str (metallic or metallic_metallic)
        Type of phase that will be filtered for. Samples include the following:
        metallic, oxide, metallic_metallic, metallic_oxide, oxide_oxide,
        metallic_aqueous oxide_aqueous, aqueous_aqueous
    """

    met_phase_lst = []

    if phase_type == 'metallic':
        for region in phase_coord:

            if len(region[1]) == 1:
                if region[1].phase_type == 'Solid':

                    is_oxide_phase = False
                    for elem in region[1].composition.elements:
                        if elem.symbol == 'O':
                            is_oxide_phase = True
                            break

                    if not is_oxide_phase:
                        met_phase_lst += [region]

    elif phase_type == 'metallic_metallic':
        for region in phase_coord:

            if len(region[1]) == 2:
                c2 = region[1][0].phase_type == 'Solid'
                c3 = region[1][1].phase_type == 'Solid'

                if c2 and c3:
                    is_oxide_phase = False

                    for elem in region[1][0].composition.elements:
                        if elem.symbol == 'O':
                            is_oxide_phase = True
                    for elem in region[1][1].composition.elements:
                        if elem.symbol == 'O':
                            is_oxide_phase = True

                    if not is_oxide_phase:
                        met_phase_lst.append(region)

    return met_phase_lst


def is_solid_phase(mat1, mat2, mat1_co=0.5):
    """Returns TRUE is there exists a all solid phase in the binary Pourbaix
    Diagram this means that the phase doesn't have any aqueous species.
    """
    mat2_co = 1 - mat1_co

    pd_b = pd_entries(mat1, mat2)

    pd = PourbaixDiagram(pd_b, {mat1: mat1_co, mat2: mat2_co})
    pl = PourbaixPlotter(pd)
    ppd = pl.pourbaix_plot_data([[-2, 16], [-3, 3]])

    pd_lst = []
    cnt = 0
    for stable_entry in ppd[0]:
        pd_lst.append([])
        pd_lst[cnt].append(ppd[0][stable_entry])
        pd_lst[cnt].append(stable_entry.entrylist)
        cnt = cnt + 1

    solidphase = False
    for i in pd_lst:
        if len(i[1]) == 1:
            if i[1][0].phase_type == 'Solid':
                solidphase = True
        if len(i[1]) == 2:
            if i[1][0].phase_type and i[1][1].phase_type == 'Solid':
                solidphase = True

    return solidphase
