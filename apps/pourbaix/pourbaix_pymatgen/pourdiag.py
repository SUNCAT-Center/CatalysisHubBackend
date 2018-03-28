from .pd_make import entry_data
from .pd_make import aq_correction
from .pd_make import stable_entr
from .pd_make import form_e
from .pd_make import mke_pour_ion_entr


def pd_entries(mtname_1, mtname_2):
    """Creates the entry objects corresponding to a binaray or single component
    Pourbaix diagram.

    Parameters:
    -----------
    mtname_1: str
        Name of element 1
    mtname_2: str
        Name of element 2

    Returns:
    --------
    all_entries: list
    """
    data = entry_data(mtname_1, mtname_2)

    ref_state_1 = str(data[1][0]['Reference Solid'])
    ref_dict_1 = {ref_state_1: data[1][0]['Reference solid energy']}
    entries_aqcorr = aq_correction(data[0])

    stable_solids_minus_h2o = stable_entr(entries_aqcorr)
    pbx_solid_entries = form_e(stable_solids_minus_h2o, entries_aqcorr)

    pbx_ion_entries_1 = mke_pour_ion_entr(
        mtname_1,
        data[1],
        stable_solids_minus_h2o,
        ref_state_1,
        entries_aqcorr,
        ref_dict_1
    )

    all_entries = pbx_solid_entries + pbx_ion_entries_1

    if mtname_1 != mtname_2:
        ref_state_2 = str(data[2][0]['Reference Solid'])
        ref_dict_2 = {ref_state_2: data[2][0]['Reference solid energy']}

        pbx_ion_entries_2 = mke_pour_ion_entr(
            mtname_2,
            data[2],
            stable_solids_minus_h2o,
            ref_state_2,
            entries_aqcorr,
            ref_dict_2
        )
        all_entries += pbx_ion_entries_2

    return all_entries
