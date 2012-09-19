"""Module with utility functions used by several Python functions."""
import os
import sys
import pickle
import PsiMod
import input
from psiexceptions import *


def kwargs_lower(kwargs):
    """Function to rebuild and return *kwargs* dictionary
    with all keys made lowercase. Should be called by every
    function that could be called directly by the user.

    """
    caseless_kwargs = {}
    if sys.hexversion < 0x03000000:
        # Python 2; we have to explicitly use an iterator
        for key, value in kwargs.iteritems():
            caseless_kwargs[key.lower()] = value
    else:
        # Python 3; an iterator is implicit
        for key, value in kwargs.items():
            caseless_kwargs[key.lower()] = value
    return caseless_kwargs


def get_psifile(fileno, pidspace=str(os.getpid())):
    """Function to return the full path and filename for psi file
    *fileno* (e.g., psi.32) in current namespace *pidspace*.

    """
    psioh = PsiMod.IOManager.shared_object()
    psio = PsiMod.IO.shared_object()
    filepath = psioh.get_file_path(fileno)
    namespace = psio.get_default_namespace()
    targetfile = filepath + 'psi' + '.' + pidspace + '.' + namespace + '.' + str(fileno)
    return targetfile


def format_molecule_for_input(mol):
    """Function to return a string of the output of
    :py:func:`input.process_input` applied to the XYZ
    format of molecule, passed as either fragmented
    geometry string *mol* or molecule instance *mol*. 
    Used to capture molecule information from database
    modules and for distributed (sow/reap) input files.
    For the reverse, see :py:func:`molutil.geometry`.

    """
    # when mol is already a string
    if isinstance(mol, basestring):
        mol_string = mol
        mol_name = ''
    # when mol is PsiMod.Molecule or qcdb.Molecule object
    else:
        # save_string_for_psi4 is the more detailed choice as it includes fragment
        #   (and possibly no_com/no_reorient) info. but this is only available
        #   for qcdb Molecules. Since save_string_xyz was added to libmints just
        #   for the sow/reap purpose, may want to unify these fns sometime.
        try:
            mol_string = mol.save_string_for_psi4()
        except AttributeError:
            mol_string = mol.save_string_xyz()

        mol_name = mol.name()

    commands = 'input.process_input("""\nmolecule %s {\n%s\n}\n""", 0)\n' % (mol_name, mol_string)
    return eval(commands)


def format_options_for_input():
    """Function to return a string of commands to replicate the
    current state of user-modified options. Used to capture C++
    options information for distributed (sow/reap) input files.

    .. caution:: Some features are not yet implemented. Buy a developer a coffee.

       - Does not cover local (as opposed to global) options.

       - Does not work with array-type options.

    """
    commands = ''
    commands += """\nPsiMod.set_memory(%s)\n\n""" % (PsiMod.get_memory())
    for chgdopt in PsiMod.get_global_option_list():
        if PsiMod.has_global_option_changed(chgdopt):
            chgdoptval = PsiMod.get_global_option(chgdopt)
            if isinstance(chgdoptval, basestring):
                commands += """PsiMod.set_global_option('%s', '%s')\n""" % (chgdopt, chgdoptval)
            elif isinstance(chgdoptval, int) or isinstance(chgdoptval, float):
                commands += """PsiMod.set_global_option('%s', %s)\n""" % (chgdopt, chgdoptval)
            else:
                raise ValidationError('Option \'%s\' is not of a type (string, int, float, bool) that can be processed.' % (chgdopt))
    return commands


def format_kwargs_for_input(filename, lmode=1, **kwargs):
    """Function to pickle to file *filename* the options dictionary
    *kwargs*. Mode *lmode* =2 pickles appropriate settings for
    reap mode. Used to capture Python options information for
    distributed (sow/reap) input files.

    """
    if lmode == 2:
        kwargs['mode'] = 'reap'
        kwargs['linkage'] = os.getpid()
    filename.write('''\npickle_kw = ("""''')
    pickle.dump(kwargs, filename)
    filename.write('''""")\n''')
    filename.write("""\nkwargs = pickle.loads(pickle_kw)\n""")
    if lmode == 2:
        kwargs['mode'] = 'sow'
        del kwargs['linkage']


def drop_duplicates(seq):
    """Function that given an array *seq*, returns an array without any duplicate
    entries. There is no guarantee of which duplicate entry is dropped.

    """
    noDupes = []
    [noDupes.append(i) for i in seq if not noDupes.count(i)]
    return noDupes


def all_casings(input_string):
    """Function to return a generator of all lettercase permutations
    of *input_string*.
    
    """
    if not input_string:
        yield ""
    else:
        first = input_string[:1]
        if first.lower() == first.upper():
            for sub_casing in all_casings(input_string[1:]):
                yield first + sub_casing
        else:
            for sub_casing in all_casings(input_string[1:]):
                yield first.lower() + sub_casing
                yield first.upper() + sub_casing


def getattr_ignorecase(module, attr):
    """Function to extract attribute *attr* from *module* if *attr*
    is available in any possible lettercase permutation. Returns
    attribute if available, None if not.
    
    """
    array = None
    for per in list(all_casings(attr)):
        try:
            getattr(module, per)
        except AttributeError:
            pass
        else:
            array = getattr(module, per)
            break

    return array


def import_ignorecase(module):
    """Function to import *module* in any possible lettercase 
    permutation. Returns module object if available, None if not.
    
    """
    modobj = None
    for per in list(all_casings(module)):
        try:
            modobj = __import__(per)
        except ImportError:
            pass
        else:
            break

    return modobj