import ast


def formation_e_data_dict():
    """ """

    # This should not be static
    direct_0 = '/home/flores12/01_ORR-MatStabScreen/01_virenv-pymatgen/01_data/03_formation_e/'
    List = open(direct_0 + 'data.py').read().splitlines()
    # Returns python list of entries_lst from read data file
    entries_lst = []
    line_cnt = 1
    for i in List:
        if not i == "":
            if i[0] == '#':
                line_cnt = line_cnt + 1
                continue
            else:
                try:
                    entries_lst.append(ast.literal_eval(i))
                except BaseException:
                    print('data_exp_form_e.formation_e_data_dict - error with line: ' + str(line_cnt))
        line_cnt = line_cnt + 1
    # Turns entry lists into dictionaries
    cf_k = "chem_formula"  # Chemical formula list key
    fe_k = "form_e"			# Formation energy key
    r_k = "reference"		# Literature reference key
    c_k = "comments"		# Comments key

    entries = []
    for i in entries_lst:
        entry_dict = {}
        entry_dict[cf_k] = i[0]
        entry_dict[fe_k] = i[1]
        entry_dict[r_k] = i[2]
        entry_dict[c_k] = i[3]
        entries.append(entry_dict)

    chem_form_lst = []
    for entry in entries:
        chem_form_lst.append(frozenset(entry[cf_k]))
    unique_entries_lst = list(list(i) for i in list(set(chem_form_lst)))

    dict = {}
    for i in unique_entries_lst:
        dict[frozenset(i)] = []
        for j in entries:
            if set(j[cf_k]) == set(i):
                dict[frozenset(i)].append(j)
    return dict


def get_entry(chemical_formula_list, data_dict):
    """ """
    key = frozenset(chemical_formula_list)

    try:
        entry = data_dict[key]
    except KeyError:
        entry = None

    return entry
