try:
    import io as StringIO
except:
    import StringIO

import ase
import ase.io


def ase_convert(instring, informat=None, outformat=None, atoms_in=False, atoms_out=False):
    """Enter a input file that is understood by ASE
    and return a string in a different format as written
    by ase.
    """
    if atoms_in:
        atoms = instring
    else:
        with StringIO.StringIO() as mem_file:
            if hasattr(instring, 'decode'):
                instring = instring.decode('utf-8')
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
