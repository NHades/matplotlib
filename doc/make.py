#!/usr/bin/env python
import fileinput
import glob
import os
import shutil
import sys

# ignore_patterns and copytree funtions are copies of what is included
# in shutil.copytree of python v2.6 and later.

try:
    WindowsError
except NameError:
    WindowsError = None

def ignore_patterns(*patterns):
    """Function that can be used as copytree() ignore parameter.

    Patterns is a sequence of glob-style patterns
    that are used to exclude files"""
    import fnmatch
    def _ignore_patterns(path, names):
        ignored_names = []
        for pattern in patterns:
            ignored_names.extend(fnmatch.filter(names, pattern))
        return set(ignored_names)
    return _ignore_patterns

def copytree(src, dst, symlinks=False, ignore=None):
    """Recursively copy a directory tree using copy2().

    The destination directory must not already exist.
    If exception(s) occur, an Error is raised with a list of reasons.

    If the optional symlinks flag is true, symbolic links in the
    source tree result in symbolic links in the destination tree; if
    it is false, the contents of the files pointed to by symbolic
    links are copied.

    The optional ignore argument is a callable. If given, it
    is called with the `src` parameter, which is the directory
    being visited by copytree(), and `names` which is the list of
    `src` contents, as returned by os.listdir():

        callable(src, names) -> ignored_names

    Since copytree() is called recursively, the callable will be
    called once for each directory that is copied. It returns a
    list of names relative to the `src` directory that should
    not be copied.

    XXX Consider this example code rather than the ultimate tool.

    """
    from shutil import copy2, Error, copystat
    names = os.listdir(src)
    if ignore is not None:
        ignored_names = ignore(src, names)
    else:
        ignored_names = set()

    os.makedirs(dst)
    errors = []
    for name in names:
        if name in ignored_names:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                copytree(srcname, dstname, symlinks, ignore)
            else:
                # Will raise a SpecialFileError for unsupported file types
                copy2(srcname, dstname)
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except Error, err:
            errors.extend(err.args[0])
        except EnvironmentError, why:
            errors.append((srcname, dstname, str(why)))
    try:
        copystat(src, dst)
    except OSError, why:
        if WindowsError is not None and isinstance(why, WindowsError):
            # Copying file access times may fail on Windows
            pass
        else:
            errors.extend((src, dst, str(why)))
    if errors:
        raise Error, errors


def copy_if_out_of_date(original, derived):
    if (not os.path.exists(derived) or
        os.stat(derived).st_mtime < os.stat(original).st_mtime):
        shutil.copyfile(original, derived)

def check_build():
    build_dirs = ['build', 'build/doctrees', 'build/html', 'build/latex',
                  '_static', '_templates']
    for d in build_dirs:
        try:
            os.mkdir(d)
        except OSError:
            pass

def sf():
    'push a copy to the sf site'
    shutil.copy('../CHANGELOG', 'build/html/_static/CHANGELOG')
    os.system('cd build/html; rsync -avz . jdh2358,matplotlib@web.sf.net:/home/groups/m/ma/matplotlib/htdocs/ -essh --cvs-exclude')

def sfpdf():
    'push a copy to the sf site'
    os.system('cd build/latex; scp Matplotlib.pdf jdh2358,matplotlib@web.sf.net:/home/groups/m/ma/matplotlib/htdocs/')

def figs():
    os.system('cd users/figures/ && python make.py')

def html():
    check_build()
    copy_if_out_of_date('../lib/matplotlib/mpl-data/matplotlibrc', '_static/matplotlibrc')
    if small_docs:
        options = "-D plot_formats=\"[('png', 80)]\""
    else:
        options = ''
    if os.system('sphinx-build %s -P -b html -d build/doctrees . build/html' % options):
        raise SystemExit("Building HTML failed.")

    figures_dest_path = 'build/html/pyplots'
    if os.path.exists(figures_dest_path):
        shutil.rmtree(figures_dest_path)
    copytree(
        'pyplots', figures_dest_path,
        ignore=ignore_patterns("*.pyc"))

    # Clean out PDF files from the _images directory
    for filename in glob.glob('build/html/_images/*.pdf'):
        os.remove(filename)

def latex():
    check_build()
    #figs()
    if sys.platform != 'win32':
        # LaTeX format.
        if os.system('sphinx-build -b latex -d build/doctrees . build/latex'):
            raise SystemExit("Building LaTeX failed.")

        # Produce pdf.
        os.chdir('build/latex')

        # Call the makefile produced by sphinx...
        if os.system('make'):
            raise SystemExit("Rendering LaTeX failed.")

        os.chdir('../..')
    else:
        print 'latex build has not been tested on windows'

def clean():
    shutil.rmtree("build", ignore_errors=True)
    shutil.rmtree("examples", ignore_errors=True)
    for pattern in ['mpl_examples/api/*.png',
                    'mpl_examples/pylab_examples/*.png',
                    'mpl_examples/pylab_examples/*.pdf',
                    'mpl_examples/units/*.png',
                    'pyplots/tex_demo.png',
                    '_static/matplotlibrc',
                    '_templates/gallery.html']:
        for filename in glob.glob(pattern):
            if os.path.exists(filename):
                os.remove(filename)

def all():
    #figs()
    html()
    latex()


funcd = {
    'figs'     : figs,
    'html'     : html,
    'latex'    : latex,
    'clean'    : clean,
    'sf'       : sf,
    'sfpdf'    : sfpdf,
    'all'      : all,
    }


small_docs = False

# Change directory to the one containing this file
current_dir = os.getcwd()
os.chdir(os.path.dirname(os.path.join(current_dir, __file__)))
copy_if_out_of_date('../INSTALL', 'users/installing.rst')


if len(sys.argv)>1:
    if '--small' in sys.argv[1:]:
        small_docs = True
        sys.argv.remove('--small')
    for arg in sys.argv[1:]:
        func = funcd.get(arg)
        if func is None:
            raise SystemExit('Do not know how to handle %s; valid args are %s'%(
                    arg, funcd.keys()))
        func()
else:
    small_docs = False
    all()
os.chdir(current_dir)
