#!/usr/bin/env python

import fractions
import functools
import re
import sqlite3

import numpy as np
from scipy.spatial import ConvexHull

import ase.units as units
from ase.atoms import string2symbols
from ase.utils import formula_hill, basestring

_solvated = []
_solids = []


def parse_formula(formula):
    aq = formula.endswith('(aq)')
    if aq:
        formula = formula[:-4]
    s = formula.endswith('(s)')
    if s:
        formula = formula[:-3]
    charge = formula.count('+') - formula.count('-')
    if charge:
        formula = formula.rstrip('+-')
    count = {}
    for symbol in string2symbols(formula):
        count[symbol] = count.get(symbol, 0) + 1
    return count, charge, aq, s


def float2str(x):
    f = fractions.Fraction(x).limit_denominator(100)
    n = f.numerator
    d = f.denominator
    if abs(n / d - f) > 1e-6:
        return '{0:.3f}'.format(f)
    if d == 0:
        return '0'
    if f.denominator == 1:
        return str(n)
    return '{0}/{1}'.format(f.numerator, f.denominator)


def solvated_ase(symbols):
    """Extract solvation energies from ASE database.

    symbols: str
        Extract only those molecules that contain the chemical elements
        given by the symbols string (plus water and H+).

    Data from:

        Johnson JW, Oelkers EH, Helgeson HC (1992)
        Comput Geosci 18(7):899.
        doi:10.1016/0098-3004(92)90029-Q

    and:

        Pourbaix M (1966)
        Atlas of electrochemical equilibria in aqueous solutions.
        No. v. 1 in Atlas of Electrochemical Equilibria in Aqueous Solutions.
        Pergamon Press, New York.

    Returns list of (name, energy) tuples.
    """

    if isinstance(symbols, basestring):
        symbols = set(string2symbols(symbols))

    if len(_solvated) == 0:
        conn = sqlite3.connect('apps/pourbaix/data/data_ase/lange_handbook.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM ase_aqueous")
        rows = cur.fetchall()
        for row in rows:
            energy = row[0]
            formula = row[1]
            name = formula + '(aq)'
            count, charge, aq, s = parse_formula(name)
            energy = float(energy) * 0.001 * units.kcal / units.mol
            _solvated.append((name, count, charge, aq, energy))
        conn.close()          

    references = []
    for name, count, charge, aq, energy in _solvated:
        for symbol in count:
            if symbol not in 'HO' and symbol not in symbols:
                break
        else:
            references.append((name, energy))
    return references

def solid_Lange(symbols,T):
    """Extract stable solid and their energies from database
       and calculate the specific Gibbs formation energies when T != 298.15 K.

    symbols: str
        Extract only those molecules that contain the chemical elements
        given by the symbols string (plus water and H+).

    Data from:

        experimental literatures:  
        D. D. Wagman, et al., The NBS Tables of Chemical Thermodynamic Properties, in J. Phys. Chem. Ref. Data, 11: 2, 1982; 
        M. W. Chase, et al., JANAF Thermochemical Tables, 3rd ed., American Chemical Society and the American Institute of Physics, 
                              1986 (supplements to JANAF appear in J. Phys. Chem. Ref. Data); 
        Thermodynamic Research Center, TRC Thermodynamic Tables, Texas A&M University, College Station, Texas;
        I. Barin and O. Knacke, Thermochemical Properties of Inorganic Substances, Springer-Verlag, Berlin, 1973; 

    Returns list of (name, energy) tuples.
    """

    if isinstance(symbols, basestring):
        symbols = set(string2symbols(symbols))

    conn = sqlite3.connect('apps/pourbaix/data/data_ase/lange_handbook.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM lange_solids")
    rows = cur.fetchall()
    if len(_solids)==0:
        for row in rows:
            formula = row[0]
            energy =  row[4]
            heat_cap_std = row[6]
            entropy_f_std = row[7]
            name = formula + '(s)'
            count, charge, aq, s = parse_formula(name)
            if energy != "NULL":
                if T == 298.15:
                    energy = float(energy) * 0.010364   #convert from kJ/mol to eV
                    _solids.append((name, count, s, energy))
                elif T != 298.15 and entropy_f_std != "NULL" and heat_cap_std != "NULL" :
                    import math  #energy unit is eV
                    energy = (float(energy) - (T - 298.15)* float(entropy_f_std) +
                             float(heat_cap_std)/1000*(T-298.15) - 
                             2.303 * T* float(heat_cap_std)/1000*math.log10(T/298.15)) *0.010364
                    _solids.append((name, count, s, energy))

    conn.close()

    references_solid = []
    for name, count, s, energy in _solids:
        for symbol in count:
            if symbol not in 'HO' and symbol not in symbols:
                break
        else:
            references_solid.append((name, energy))
    return references_solid

def bisect(A, X, Y, f):
    a = []
    for i in [0, -1]:
        for j in [0, -1]:
            if A[i, j] == -1:
                A[i, j] = f(X[i], Y[j])
            a.append(A[i, j])

    if np.ptp(a) == 0:
        A[:] = a[0]
        return
    if a[0] == a[1]:
        A[0] = a[0]
    if a[1] == a[3]:
        A[:, -1] = a[1]
    if a[3] == a[2]:
        A[-1] = a[3]
    if a[2] == a[0]:
        A[:, 0] = a[2]
    if not (A == -1).any():
        return
    i = len(X) // 2
    j = len(Y) // 2
    bisect(A[:i + 1, :j + 1], X[:i + 1], Y[:j + 1], f)
    bisect(A[:i + 1, j:], X[:i + 1], Y[j:], f)
    bisect(A[i:, :j + 1], X[i:], Y[:j + 1], f)
    bisect(A[i:, j:], X[i:], Y[j:], f)


def print_results(results):
    total_energy = 0.0
    print('reference    coefficient      energy')
    print('------------------------------------')
    for name, coef, energy in results:
        total_energy += coef * energy
        if abs(coef) < 1e-7:
            continue
        print('{0:14}{1:>10}{2:12.3f}'.format(name, float2str(coef), energy))
    print('------------------------------------')
    print('Total energy: {0:22.3f}'.format(total_energy))
    print('------------------------------------')


class Pourbaix:
    def __init__(self, references, T, ions_conc, formula=None,**kwargs):
        """Pourbaix object.

        references: list of (name, energy) tuples
            Examples of names: ZnO2, H+(aq), H2O(aq), Zn++(aq), ...
        ions_conc: dictionary of {ion: concentration}
            Examples: {Zn++(aq): 1e-06,
                       Cu++(aq): 1e-04,
                       ...}
        formula: str
            Stoichiometry.  Example: ``'ZnO'``.  Can also be given as
            keyword arguments: ``Pourbaix(refs, Zn=1, O=1)``.
        T: float
            Temperature in Kelvin.
        """

        if formula:
            assert not kwargs
            kwargs = parse_formula(formula)[0]

        self.kT = units.kB * T
        self.ions_conc = {}
        self.ions_conc = ions_conc
        self.references = []
        for name, energy in references:
            if name == 'O':
                continue
            count, charge, aq, s = parse_formula(name)
            for symbol in count:
                if aq:
                    if not (symbol in 'HO' or symbol in kwargs):
                        break
                else:
                    if symbol not in kwargs:
                        break
            else:
                self.references.append((count, charge, aq, energy, name))

        self.references.append(({}, -1, False, 0.0, 'e-'))  # an electron

        self.count = kwargs

        if 'O' not in self.count:
            self.count['O'] = 0

        self.N = {'e-': 0, 'H': 1}
        for symbol in kwargs:
            if symbol not in self.N:
                self.N[symbol] = len(self.N)

    def decompose(self, U, pH, verbose=True):
        """Decompose material.

        U: float
            Potential in V.
        pH: float
            pH value.
        verbose: bool
            Default is True.
        concentration: float
            Concentration of solvated references.

        Returns optimal coefficients and energy.
        """

        alpha = np.log(10) * self.kT
#         entropy = -np.log(concentration) * self.kT

        # We want to minimize np.dot(energies, x) under the constraints:
        #
        #     np.dot(x, eq2) == eq1
        #
        # with bounds[i,0] <= x[i] <= bounds[i, 1].
        #
        # First two equations are charge and number of hydrogens, and
        # the rest are the remaining species.

        eq1 = [0, 0] + list(self.count.values())
        eq2 = []
        energies = []
        bounds = []
        names = []
#         ion_names = []

        
        for count, charge, aq, energy, name in self.references:
            eq = np.zeros(len(self.N))
            eq[0] = charge
            for symbol, n in count.items():
                eq[self.N[symbol]] = n
            eq2.append(eq)
            if name in ['H2O(aq)', 'H+(aq)', 'e-']:
                bounds.append((-np.inf, np.inf))
                if name == 'e-':
                    energy = -U
                elif name == 'H+(aq)':
                    energy = -pH * alpha
            else:
                bounds.append((0, 1))
                if aq: 
                    # energy -= -np.log(1e-6) * self.kT
                    for dic in self.ions_conc:
                        for ion_name, conc in dic.items():
                            if name == ion_name.split('_')[1]:
                                energy  -= -np.log(float(conc)) * self.kT

            if verbose:
                print('{0:<5}{1:10}{2:10.3f}'.format(len(energies),
                                                     name, energy))
            energies.append(energy)
            names.append(name)
        # print(self.ions_conc)

        try:
            from scipy.optimize import linprog
        except ImportError:
            from ase.utils._linprog import linprog
        result = linprog(energies, None, None, np.transpose(eq2), eq1, bounds)

        if verbose:
            print_results(zip(names, result.x, energies))

        return result.x, result.fun


    def diagram(self, U, pH,plot=True, show=False, ax=None):
        """Calculate Pourbaix diagram.

        U: list of float
            Potentials in V.
        pH: list of float
            pH values.
        plot: bool
            Create plot.
        show: bool
            Open graphical window and show plot.
        ax: matplotlib axes object
            When creating plot, plot onto the given axes object.
            If none given, plot onto the current one.
        """
        a = np.empty((len(U), len(pH)), int)
        a[:] = -1
        colors = {}
        f = functools.partial(self.colorfunction, colors=colors)
        bisect(a, U, pH, f)
        compositions = [None] * len(colors)
        names = [ref[-1] for ref in self.references]
        for indices, color in colors.items():
            compositions[color] = ' + '.join(names[i] for i in indices
                                             if names[i] not in
                                             ['H2O(aq)', 'H+(aq)', 'e-'])
        text  = []
        x_loc = []
        y_loc = []
        names  = []
        for i, name in enumerate(compositions):
            b = (a == i)
            x = np.dot(b.sum(1), U) / b.sum()
            y = np.dot(b.sum(0), pH) / b.sum()
            # name = re.sub('(\S)([+-]+)', r'\1$^{\2}$', name)
            # name = re.sub('(\d+)', r'$_{\1}$', name)

            x_loc.append(x)
            y_loc.append(y)
            names.append(name)
            text.append((x, y, name))

        if plot:
            import matplotlib.pyplot as plt
            import matplotlib.cm as cm
            # import plotly.plotly as py
            from mpld3 import plugins


            if ax is None:
                # ax = plt.gca()
                fig, ax = plt.subplots()

            # rasterized pcolormesh has a bug which leaves a tiny
            # white border.  Unrasterized pcolormesh produces
            # unreasonably large files.  Avoid this by using the more
            # general imshow.
            ax.imshow(a, cmap=cm.Accent,
                      extent=[min(pH), max(pH), min(U), max(U)],
                      origin='lower',
                      aspect='auto')
            
            labels_loc = ax.scatter(y_loc, x_loc)
            labels_text = [name for name in names]

            tooltip = plugins.PointLabelTooltip(labels_loc, labels_text)
            plugins.connect(fig,tooltip)

            ax.set_xlabel('pH')
            ax.set_ylabel('U(V)')
            ax.set_xlim(min(pH), max(pH))
            ax.set_ylim(min(U), max(U))
            # data_url = py.plot_mpl(fig)

            if show:
                  plt.show()

        return a, compositions, text, x_loc, y_loc, labels_text, fig #data_url 


    def colorfunction(self, U, pH, colors):
        coefs, energy = self.decompose(U, pH, verbose=False)
        indices = tuple(sorted(np.where(abs(coefs) > 1e-7)[0]))
        color = colors.get(indices)
        if color is None:
            color = len(colors)
            colors[indices] = color
        return color
       
