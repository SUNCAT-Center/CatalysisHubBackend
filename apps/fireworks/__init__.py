"""
This code schedule a hierarchic workflow for calculating
adsorption energies.
"""
import os
import pprint
import string
try:
    import io as StringIO
except:
    import StringIO

import flask
import fireworks as fw

import ase
import ase.io
import ase.atoms
try:
    import espresso
except:
    print("Warning: espresso calculator not available.")
    espresso = None

import apps.catKitDemo


# set up the LaunchPad
launchpad = fw.LaunchPad(
    host=os.environ['FW_HOST'],
    name=os.environ['FW_DATABASE'],
    username=os.environ['FW_USER'],
    password=os.environ['FW_PASSWORD']
)

# Define the ase-espresso keys we will use.
keys = {
    'mode': 'relax',
    'opt_algorithm': 'bfgs',
    'xc': 'RPBE',
    'outdir': '.',
    'output': {'removesave': True},
    'pw': 400,
    'dw': 4000,
    'dipole': {'status': True},
    'kpts': (4, 4, 1),
    'calcstress': True,
    'convergence': {
        'energy': 1e-5,
        'mixing': 0.35}
}

SCRIPT_TEMPLATE = """
from ase import Atoms
from ase.io import write
${calculator_import}

keys = ${keys}

# Create the atoms object
${atoms}
atoms = images[0]
atoms.info = keys

# Calculate the relaxation
calc = ${calculator_constructor}(**keys)
atoms.set_calculator(calc)
atoms.get_potential_energy()

# Save the compressed calculator file so that we can use it for later.
#calc.save_flev_output()
"""


def create_gas_phase_tasks(calculation):
    tasks = []
    for dft_code in calculation.keys():
        for dft_functional in calculation[dft_code].keys():
            for gp_name in calculation[dft_code][dft_functional].get('gas', []):
                atoms = calculation[dft_code][dft_functional]['gas'][gp_name]

                with StringIO.StringIO() as outfile:
                    ase.io.write(outfile, atoms, format='py')
                    atoms_string = outfile.getvalue()

                firetask = fw.ScriptTask(
                    shell_exe='/home/vossj/suncat/bin/python',
                    script=string.Template(SCRIPT_TEMPLATE).safe_substitute(
                        keys=keys,
                        atoms=atoms_string,
                        calculator_import='from espresso import espresso',
                        calculator_constructor='espresso',
                    )
                )
                firework = fw.Firework(firetask, name=gp_name)
                tasks.append(firework)
    return tasks


def create_bulk_tasks(calculation):
    tasks = []
    for dft_code in calculation.keys():
        for dft_functional in calculation[dft_code].keys():
            for structure in calculation[dft_code][dft_functional]:
                if structure == 'gas':
                    continue
                atoms = calculation[dft_code][
                    dft_functional][structure]['bulk']
                with StringIO.StringIO() as outfile:
                    ase.io.write(outfile, atoms, format='py')
                    atoms_string = outfile.getvalue()

                firetask = fw.ScriptTask(
                    shell_exe='/home/vossj/suncat/bin/python',
                    script=string.Template(SCRIPT_TEMPLATE).safe_substitute(
                        keys=keys,
                        atoms=atoms_string,
                        calculator_import='from espresso import espresso',
                        calculator_constructor='espresso',
                    )
                )
                firework = fw.Firework(
                    firetask, name='{structure}_bulk'.format(**locals()))
                tasks.append(firework)
    return tasks


def create_slab_tasks(calculation):
    tasks = []
    for dft_code in calculation.keys():
        for dft_functional in calculation[dft_code].keys():
            for structure in calculation[dft_code][dft_functional]:
                if structure == 'gas':
                    continue
                for facet in calculation[dft_code][dft_functional][structure]:
                    if facet == 'bulk':
                        continue
                    for site in calculation[dft_code][dft_functional][structure][facet]:
                        atoms = calculation[dft_code][
                            dft_functional][structure][facet][site]
                        with StringIO.StringIO() as outfile:
                            ase.io.write(outfile, atoms, format='py')
                            atoms_string = outfile.getvalue()

                        firetask = fw.ScriptTask(
                            shell_exe='/home/vossj/suncat/bin/python',
                            script=string.Template(SCRIPT_TEMPLATE).safe_substitute(
                                keys=keys,
                                atoms=atoms_string,
                                calculator_import='from espresso import espresso',
                                calculator_constructor='espresso',
                            )
                        )
                        site_only = site.split('__')[-1]
                        firework = fw.Firework(
                            firetask, name='{facet}__{site_only}'.format(**locals()))
                        tasks.append(firework)
    return tasks


def create_collector_tasks(calculation):
    firetask = fw.ScriptTask(
        shell_exe='/home/vossj/suncat/bin/python',
        script="""
print('This script shall collect all the important data')
print('But nothing here to see, yet.')
"""
    )
    firework = fw.Firework(firetask, name='collector')
    return [firework]


fireworks_bp = flask.Blueprint('fireworks', __name__)


@fireworks_bp.route('/schedule_workflows', methods=['GET', 'POST'])
def schedule_workflows(request=None):
    request = flask.request if request is None else request
    if type(request.args) is str:
        request.args = json.loads(request.args)

    calculations = apps.catKitDemo.generate_dft_input(
        request, return_data=True)
    messages = {}

    for i, calculation in enumerate(calculations):
        gas_phase_tasks = create_gas_phase_tasks(calculation)
        bulk_tasks = create_bulk_tasks(calculation)
        slab_tasks = create_slab_tasks(calculation)
        collector_tasks = create_collector_tasks(calculation)

        # declare job dependecy
        task_dependency = {}
        for bulk_task in bulk_tasks:
            task_dependency[bulk_task] = slab_tasks

        for task in gas_phase_tasks + slab_tasks:
            task_dependency[task] = collector_tasks

        workflow = fw.Workflow(bulk_tasks
                               + gas_phase_tasks
                               + slab_tasks
                               + collector_tasks,
                               task_dependency,
                               name='calculation')

        messages.update(launchpad.add_wf(workflow,))
    return flask.jsonify({
        'messages': messages,
    })


if __name__ == "__main__":
    calculations = [None]
    schedule_workflows(calculations, launchpad)
