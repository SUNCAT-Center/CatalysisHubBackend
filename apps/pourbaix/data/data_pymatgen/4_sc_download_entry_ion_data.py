from element_list import ElementList, ElemList_mod
from pymatgen.matproj.rest import MPRester
from monty.json import MontyEncoder, MontyDecoder
import json
import os
import warnings; warnings.filterwarnings('ignore')

def create_fle_entry_ion(el_0,el_1):
	"""
	Creates a directory and creates 3 files:
		ion_data_1: contains ion_data for el_0 relevent to Pourbaix Diagrams
		ion_data_2: contains ion_data for el_1 relevent to Pourbaix Diagrams
		mp_entries.txt: entry data from Materials Project
	Args:
		el_0: Elemental symbol (type: string) of first element
		el_1: Elemental symbol (type: string) of second element
	"""

	fle_nme = el_0+'_'+el_1
	os.makedirs(fle_nme)
	os.chdir(fle_nme)

	mpr = MPRester('TA7RCwHn3PGaN2m1')
	if el_0==el_1:
		entries = mpr.get_entries_in_chemsys([el_0, 'O', 'H'])
	else:
		entries = mpr.get_entries_in_chemsys([el_0, el_1, 'O', 'H'])

	ion_dict_1 = mpr._make_request('/pourbaix_diagram/reference_data/'+el_0)
	ion_dict_2 = mpr._make_request('/pourbaix_diagram/reference_data/'+el_1)

	## Writing the Material Project entries to file ##
	tmp = json.dumps(entries, cls=MontyEncoder)
	f = open('mp_entries.txt','w')
	f.write(tmp)
	f.close()

	## Writing ion data to file ##
	f = open('ion_data_1.txt','w')
	json.dump(ion_dict_1, f)
	f.close()

	f = open('ion_data_2.txt','w')
	json.dump(ion_dict_2, f)
	f.close()

	os.chdir('..')

def chk_dir_finished(el_0,el_1):
	"""
	Checks if a directory has finished being written to and returns True if so
	Used to restart script after failures

	Args:
		el_0: Elemental symbol (type: string) of first element
		el_1: Elemental symbol (type: string) of second element
	"""
	dir_nme = el_0+'_'+el_1
	if 	os.path.isfile(dir_nme+'/'+'ion_data_1.txt')==True and \
		os.path.isfile(dir_nme+'/'+'ion_data_2.txt')==True and \
		os.path.isfile(dir_nme+'/'+'mp_entries.txt')==True:

		return True
		print el_0+'_'+el_1+' - finished'

	else:
		return False
		print el_0+'_'+el_1+' - not finished'

def del_emp_dir(el_0,el_1):
	"""
	Deletes folder for a binary pair if it has no data written in it
	Clear working directory of unfinished folders so that create_fle_entry_ion
	can write data correctly

	Args:
		el_0: Elemental symbol (type: string) of first element
		el_1: Elemental symbol (type: string) of second element
	"""

	dir_nme = el_0+'_'+el_1
	if 	os.path.isdir(dir_nme)==True and \
		chk_dir_finished(el_0,el_1)==False:

		os.rmdir(dir_nme)

###############################################################################
no_exp_data =   ['Ne','Ar','Kr','Rh','Xe','Pm','Hf','Ta','Ir','Po','At','Rn',
		'Fr','Ra','Ac','Pa','Np','Am','Cm','Bk','Cf','Es','Fm','Md','No']

elem_0 = ElementList().trans_met
elem_1 = ElementList().trans_met

tot_folders = 0
for el_0 in elem_0:
        if el_0.symbol in no_exp_data: continue
        for el_1 in elem_1:
                if el_1.symbol in no_exp_data: continue
                tot_folders=tot_folders+1.
print 'Total number of folders: '+str(tot_folders)

cnt = 0
for el_0 in elem_0:
	if el_0.symbol in no_exp_data: continue
	for el_1 in elem_1:
		cnt=cnt+1.
		if el_1.symbol in no_exp_data: continue
		if chk_dir_finished(el_0.symbol,el_1.symbol)==True: continue
		del_emp_dir(el_0.symbol,el_1.symbol)
		print el_0.symbol+'_'+el_1.symbol+'	start'
		create_fle_entry_ion(el_0.symbol,el_1.symbol)
		progress = 100*cnt/tot_folders

		print '	finished -- progress: '+str(progress)+'%'
		print '____________________________________'
	print '############## '+el_0.symbol+' done '+'#############'
	print '####################################'
	print ' '
