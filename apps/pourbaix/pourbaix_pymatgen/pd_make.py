from pymatgen import MPRester
from pymatgen import Element
from pymatgen.core.ion import Ion
from pymatgen.entries.compatibility import MaterialsProjectAqueousCompatibility
from pymatgen.analysis.phase_diagram import PhaseDiagram
from pymatgen.analysis.pourbaix.entry import PourbaixEntry
from pymatgen.analysis.pourbaix.entry import IonEntry
import warnings
import json
import os
from monty.json import MontyDecoder
from .entry_methods import base_atom
warnings.filterwarnings('ignore')


def entry_data(mtnme_1, mtnme_2, direct_0='apps/pourbaix/data/data_pymatgen', mprester_key=None):
    """Obtaining entry and ion data from local source.

    Parameters:
    -----------
    mtnme_1: str
        Material 1
    mtnme_2: str
        Material 2
    direct_0: dict
        root path to local entry database for binary systems

    Returns:
    --------
    data: list ["entries", "ion_data_1", "ion_data_2"]
        data for producing the pourbaix diagram
    """
    direct = os.path.join(direct_0, '_'.join([mtnme_1, mtnme_2]))
    entry_data = os.path.join(direct, 'mp_entries.txt')

    # Load entry data
    # print(os.path.abspath(entry_data))
    # print(os.path.abspath('.'))
    if os.path.exists(entry_data):
        with open(entry_data, 'r') as f:
            entries = json.load(f, cls=MontyDecoder)

    elif mprester_key is not None:
        mpr = MPRester(mprester_key)
        if mtnme_1 != mtnme_2:
            entries = mpr.get_entries_in_chemsys([mtnme_1, mtnme_2, 'O', 'H'])
        else:
            entries = mpr.get_entries_in_chemsys([mtnme_1, 'O', 'H'])

    else:
        raise ValueError("No local data entry, mprester_key required.")

    # Load ion_data 1
    ion1_data = os.path.join(direct, 'ion_data_1.txt')
    if os.path.exists(ion1_data):
        with open(ion1_data, 'r') as f:
            ion_dict_1 = json.load(f)

    elif mprester_key is not None:
        mpr = MPRester(mprester_key)
        ion_dict_1 = mpr._make_request(
            '/pourbaix_diagram/reference_data/' + mtnme_1
        )

    else:
        raise ValueError("No local ion1_data, mprester_key required.")

    data = [entries, ion_dict_1]

    # Get ion_data 2
    if mtnme_1 != mtnme_2:
        ion2_data = os.path.join(direct, 'ion_data_2.txt')
        if os.path.exists(ion2_data):
            with open(ion2_data, 'r') as f:
                ion_dict_2 = json.load(f)

        elif mprester_key is not None:
            ion_dict_2 = mpr._make_request(
                '/pourbaix_diagram/reference_data/' + mtnme_2
            )

        else:
            raise ValueError("No local ion1_data, mprester_key required.")

        data += [ion_dict_2]

    return data


def remove_duplicate_entries(entry_list):
    """ """
    entry_list_new = list()
    for entry in entry_list:
        if not contains_entry(entry_list_new, entry):
            entry_list_new.append(entry)

    return entry_list_new


def contains_entry(entry_list, ent):
    """Helpful to filter duplicate entries, if entry
    is in entry_list, return True

    Parameters:
    -----------
    entry_list: list
        pymatgen entries to consider
    entry: object
        entry which will be analyzed
    """

    ent_id = ent.entry_id
    ent_E = ent.energy_per_atom
    ent_redfor = ent.composition.reduced_formula
    for e in entry_list:
        if e.entry_id == ent_id or (abs(ent_E - e.energy_per_atom) < 1e-6 and
                                    ent_redfor == e.composition.reduced_formula):
            return True


def aq_correction(entries):
    """Applies the Materials Project Aqueous Compatibility scheme for mixing GGA
    and GGA+U to a list of entries.
    Removes entries which aren't compatible with the mixing scheme

    Parameters:
    -----------
    entries: list
        entries on which the correction will be applied
    """
    # Implements the GGA/GGA+U mixing scheme,
    aqcompat = MaterialsProjectAqueousCompatibility()

    entries_aqcorr = list()
    for entry in entries:
        # Corrections, if none applicable, gets rid of entry
        aq_corrected_entry = aqcompat.process_entry(entry)

        if not contains_entry(
                entries_aqcorr,
                aq_corrected_entry):
            entries_aqcorr.append(aq_corrected_entry)

    return entries_aqcorr


def stable_entr(entries_aqcorr):
    """Evaluate a entries in list for stability and discard unstable entries
    Remove H2, O2, H2O, and H2O2 from the list
    Calculate the formation using the species in the chemical ensemble

    Parameters:
    -----------
    entries_aqcorr: list
        entries, usually they have been run through the aqueous
        compatibility module
    """
    pd = PhaseDiagram(entries_aqcorr)
    stable_solids = pd.stable_entries
    stable_solids_minus_h2o = [
        entry for entry in stable_solids
        if entry.composition.reduced_formula not in ["H2", "O2", "H2O", "H2O2"]
    ]

    return stable_solids_minus_h2o


def form_energy(entry, solid_ref_energy_dict):
    """Calculating the Formation Energy"""

    # mp-12957, half of O2 (WITH CORRECTION)
    e_o = -5.25225891875

    # mp-754417, half of H2 (WITH CORRECTION)
    e_h = -3.6018845

    ref_dict = {}
    ref_dict['O'] = e_o
    ref_dict['H'] = e_h

    z = ref_dict.copy()
    z.update(solid_ref_energy_dict)
    ref_dict = z

    elem_dict = entry.composition.get_el_amt_dict()
    entry_e = entry.energy

    for elem in entry.composition.elements:
        elem_num = elem_dict[elem.symbol]
        entry_e = entry_e - elem_num * ref_dict[elem.symbol]

    return entry_e


def form_e(stable_solids_minus_h2o, entries_aqcorr):
    """Calculate the formation energy for the entries in stable_solids_minus_h2o
    Reduce by stoicheometric factor if applicable (ex. Fe4O4)

    Parameters:
    -----------
    stable_solids_minus_h2o: list
        stable solids without O2, H2O, H2, and H2O2 (from stable_entr)
    entries_aqcorr: list
        entries before being modified by stable_entr
    """
    base_at = base_atom(stable_solids_minus_h2o)
    d = {}
    for i in stable_solids_minus_h2o:
        if i.name in base_at:
            d[i.name] = i.energy_per_atom

    pbx_solid_entries = []
    for entry in stable_solids_minus_h2o:
        pbx_entry = PourbaixEntry(entry)
        # Replace E with form E relative to ref elements
        pbx_entry.g0_replace(form_energy(entry, d))
        # pbx_entry.g0_replace(pd.get_form_energy(entry)) #Replace E with form
        # E relative to ref elements
        # Reduces parameters by stoich factor (ex. Li2O2 -> LiO)
        pbx_entry.reduced_entry()
        pbx_solid_entries.append(pbx_entry)

    return pbx_solid_entries


def ref_entry_find(stable_solids_minus_h2o, ref_state):
    """

    Parameters:
    -----------
    stable_solids_minus_h2o:
    ref_state:
    """
    for entry in stable_solids_minus_h2o:
        if entry.composition.reduced_formula == ref_state:
            ref_entry = entry
            break
        else:
            ref_entry = []

    if not ref_entry:
        print('05 - Error with ' + ref_state + ' solid reference data')
        return '05 - Error with ' + ref_state + ' solid reference data'

    return ref_entry


def ref_entry_stoich(ref_entry):
    """ """
    ref_stoich_fact = ref_entry.composition.get_reduced_composition_and_factor()[1]

    return ref_stoich_fact


def mke_pour_ion_entr(
        mtnme,
        ion_dict,
        stable_solids_minus_h2o,
        ref_state,
        entries_aqcorr,
        ref_dict
):
    """ """
    pd = PhaseDiagram(entries_aqcorr)

    ref_entry = ref_entry_find(stable_solids_minus_h2o, ref_state)
    ref_stoich_fact = ref_entry_stoich(ref_entry)

    # Calculate DFT reference E for ions (Persson et al, PRB (2012))
    # DFT formation E, normalized by composition "factor"
    dft_for_e = pd.get_form_energy(ref_entry) / ref_stoich_fact
    # Difference of DFT form E and exp for E of reference
    ion_correction_1 = dft_for_e - ref_dict[ref_state]

    el = Element(mtnme)
    pbx_ion_entries_1 = []
    for id in ion_dict:
        # Ion name-> Ion comp name (ex. Fe[3+] -> Ion: Fe1 +3)
        comp = Ion.from_formula(id['Name'])
        # comp.composition[el] : number of Fe atoms in ion
        # number of element atoms in reference
        num_el_ref = (ref_entry.composition[el]) / ref_stoich_fact
        # Stoicheometric factor for ionic correction
        factor = comp.composition[el] / num_el_ref
        # (i.e. Fe2O3 ref but calc E for Fe[2+] ion)
        energy = id['Energy'] + ion_correction_1 * factor
        pbx_entry_ion = PourbaixEntry(IonEntry(comp, energy))
        pbx_entry_ion.name = id['Name']
        pbx_ion_entries_1.append(pbx_entry_ion)

    return pbx_ion_entries_1
