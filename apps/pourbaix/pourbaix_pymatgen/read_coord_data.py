from monty.json import MontyDecoder
import json
import os


def read_coord_data(elem_1, elem_2, mat1_co=0.5):
    """ """
    coord = []

    # This should not be static
    direct = '/home/flores12/01_ORR-MatStabScreen/01_virenv-pymatgen/02_loc_PD_data/02_local_PD_line_data/'

    direct_elem = direct + elem_1 + '_' + elem_2 + '/'

    reg_lst = os.listdir(direct_elem)
    reg_lst.sort(key=int)

    os.chdir(direct_elem)
    reg_cnt = 0
    for reg in reg_lst:
        coord.append([])
        coord[reg_cnt].append([])

        # Adding Pourbaix Object/Entry Data
        os.chdir(reg)
        os.chdir('pourb_entry')

        pourb_ent_open_0 = open('pourb_entry_0.txt', 'r')
        pourb_ent_fle_0 = pourb_ent_open_0.read()
        pourb_ent_data_0 = json.loads(pourb_ent_fle_0, cls=MontyDecoder)

        if len(os.listdir('.')) == 2:

            pourb_ent_open_1 = open('pourb_entry_1.txt', 'r')
            pourb_ent_fle_1 = pourb_ent_open_1.read()
            pourb_ent_data_1 = json.loads(pourb_ent_fle_1, cls=MontyDecoder)

            coord[reg_cnt][0].append(pourb_ent_data_0)
            coord[reg_cnt][0].append(pourb_ent_data_1)
        else:
            coord[reg_cnt][0].append(pourb_ent_data_0)

        os.chdir('..')
        os.chdir('pourb_lines')
        pourb_lne_open = open('pourb_lines.txt', 'r')
        pourb_lne_data = json.load(pourb_lne_open)

        coord[reg_cnt].insert(0, pourb_lne_data)
        os.chdir('../..')

        reg_cnt = reg_cnt + 1

    return coord
