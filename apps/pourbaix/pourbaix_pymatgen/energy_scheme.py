from .pd_make import entry_data
from .entry_methods import entry_remove
from .entry_methods import norm_e
from .entry_methods import contains_element
from .entry_methods import pure_atoms_return

# O2, H2 Reference State
e_o = -4.93552791875		# mp-12957, half of O2 - No entropy term
e_h = -3.2397			# mp-754417, half of H2 - No entropy term

e_h2 = 2 * e_h
e_o2 = 2 * e_o


def form_e_all_oxides(element, correction_=True, direct_0='data'):
    """OUTLINE:
    1. Get all entries in the chemical ensemble for 1 element and oxygen
    2. Extract all of the oxide species
    3. Extract the pure metallic references
    4. Apply correction scheme to entries
    5. Calculate the formation energy for the oxides
    """

    all_entries = entry_data(
        element,
        element,
        direct_0,
    )['entries']

    oxygen_entries = contains_element(all_entries, 'O')
    hydrogen_entries = contains_element(all_entries, 'H')
    entries_no_h = [
        entry for entry in oxygen_entries if entry not in hydrogen_entries]

    oxides = entry_remove(entries_no_h, 'O2')

    elem_ref = pure_atoms_return(all_entries)[0]
    elem_ref_e = norm_e(elem_ref)

    if not elem_ref.name == element:
        print('calc_form_e - The reference atom is not the same as the element')

    # start_fold - Formation Energy
    form_e_lst = []
    for oxide in oxides:
        oxide_e = norm_e(oxide, correction=correction_)

        elem_coef = oxide.composition.get_el_amt_dict(
        )[element] / oxide.composition.get_integer_formula_and_factor()[1]
        oxygen_coef = oxide.composition.get_el_amt_dict(
        )['O'] / oxide.composition.get_integer_formula_and_factor()[1]

        form_e = oxide_e - elem_coef * elem_ref_e - oxygen_coef * e_o

        elem_comp_lst = []
        elem_comp_lst.append(str(element) + '%g' % (elem_coef))
        elem_comp_lst.append('O' + '%g' % (oxygen_coef))

        entry_dict = {}
        entry_dict['form_e'] = form_e
        entry_dict['entry'] = oxide.name
        entry_dict['entry_elements'] = elem_comp_lst

        form_e_lst.append(entry_dict)

        if oxide.name == 'Pt3O4':

            print('Oxide Energy: ' + str(oxide_e))
            print('Element Reference Energy: ' + str(elem_ref_e))
            print('Oxygen Energy: ' + str(e_o))
            print('_____')
            print('Element Coefficient: ' + str(elem_coef))
            print('Oxygen Coefficient: ' + str(oxygen_coef))
            print('_____')
            print('Formation Energy: ' + str(form_e))
            print('############')

    return form_e_lst
