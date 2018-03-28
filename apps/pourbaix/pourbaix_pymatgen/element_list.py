from pymatgen.core.periodic_table import Element


class ElementList(object):
    """Class for creating element lists and ranges
    By default the first list created is in order of atomic number.
    """

    def __init__(self, atom_num_lst=[[]]):
        self.atom_num_lst = atom_num_lst
        if not atom_num_lst == [[]]:
            self.list = self.mk_lst_atnum()
        self.trans_met = self.mk_lst_trans_met()

    def mk_lst_atnum(self):
        """Makes list of elements from the atom_num_lst input"""
        elem_rnge = []
        for i in self.atom_num_lst:
            el_strt = i[0]
            el_end = i[1]
            rnge_sect = list(range(el_strt, el_end + 1))
            elem_rnge.extend(rnge_sect)
        elements = []
        for i in elem_rnge:
            element = Element.from_Z(i)  # Indice -> pymatgen element object
            elements.append(element)

        return elements

    def mk_lst_trans_met(self):
        """Produces list of transition metals in order of atomic number"""
        elem_rnge_I = [[21, 30], [39, 44], [46, 48], [74, 76], [78, 80]]
        elem_rnge = []
        for i in elem_rnge_I:
            el_strt = i[0]
            el_end = i[1]
            rnge_sect = list(range(el_strt, el_end + 1))
            elem_rnge.extend(rnge_sect)
        elements = []
        for i in elem_rnge:
            element = Element.from_Z(i)  # Indice -> pymatgen element object
            elements.append(element)

        return elements


class ElemList_mod(object):
    def __init__(self, elem_lst):
        self.elem_lst = elem_lst

    @property
    def sort(self, srt_type='group_num'):
        """Sorts element entries

        Parameters:
        -----------
        srt_type: str
            DEFAULT: group_num, sorts by group number with lowest group
            number first, and lowest period first.
        """
        if srt_type == 'group_num':
            elem_lst = self.elem_lst
            elem_lst_sorted = elem_lst[:]
            elem_lst_sorted.sort(key=lambda x: x.group)
            return elem_lst_sorted

    def remove(self, element):
        """Removes element from element list

        Parameters:
        element: list of objects
            If only 1 element just 1 element number or chemical symbol
            name "or" atomic number of the element to be removed
        """
        elem_lst_0 = self.elem_lst
        if isinstance(element, type([])):
            for elem in element:
                if isinstance(elem, type('string')):
                    # Find the occurance of input 'elem' in the list and return
                    elem_lst_0 = [x for x in elem_lst_0 if not x.name == elem]
                elif isinstance(elem, type(2)):
                    elem_lst_0 = [
                        x for x in elem_lst_0 if not x.number == elem]

            return elem_lst_0

        if isinstance(element, type('string')):
            # Find the occurance of input 'elem' in the list and returns it
            elem_lst_new = [x for x in self.elem_lst if not x.name == element]

            return elem_lst_new

        elif isinstance(element, type(2)):
            elem_lst_new = [
                x for x in self.elem_lst if not x.number == element]

            return elem_lst_new


def elem_str_mke(elem_lst):
    """ """
    elem_str = []
    for i in elem_lst:
        elem_str.append(i.symbol)

    return elem_str
