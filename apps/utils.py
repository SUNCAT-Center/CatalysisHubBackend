try:
    import io as StringIO
except:
    import StringIO

import ase
import ase.io

VALID_FORMATS = ["abinit", "castep-cell", "cfg", "cif", "dlp4", "eon", "espresso-in", "extxyz", "findsym",
                     "gen", "gromos", "json", "jsv", "nwchem", "proteindatabank", "py", "traj", "turbomole", "v-sim", "vasp", "xsf", "xyz"]



def ase_convert(instring, informat=None, outformat=None, atoms_in=False, atoms_out=False):
    """Enter a input file that is understood by ASE
    and return a string in a different format as written
    by ase.
    """
    if not outformat:
        outformat = 'cif'

    if informat not in VALID_FORMATS:
        return {
            "error": "informat {informat} is invalid. Should be on of {VALID_FORMATS}".format(**dict(globals(), **locals() )),
        }
    if outformat not in VALID_FORMATS:
        return {
            "error": "outFormat {outformat} is invalid. Should be on of {VALID_FORMATS}".format(**dict(globals(), **locals() )),
        }

    if atoms_in:
        atoms = instring
    else:
        if informat == 'traj':
            constr = StringIO.BytesIO
        else:
            constr = StringIO.StringIO

        with constr() as mem_file:
            try:
                if hasattr(instring, 'decode'):
                    instring = instring.decode('UTF-8')
            except Exception as e:
                print(informat)
                print(e)

            mem_file.write(instring)
            mem_file.seek(0)
            atoms = ase.io.read(mem_file, format=informat)

    if atoms_out:
        outstring = atoms
    else:
        with StringIO.StringIO() as mem_file:
            ase.io.write(mem_file, atoms, format=outformat)
            outstring = mem_file.getvalue()

    return outstring
