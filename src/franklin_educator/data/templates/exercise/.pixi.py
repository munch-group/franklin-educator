import sys, os, re
import nbformat
from pathlib import Path
# import importlib_resources
import subprocess, shlex, shutil


module_to_conda_package = {
    "sklearn": "scikit-learn",
    "cv2": "opencv",
    "PIL": "pillow",
    "bs4": "beautifulsoup4",
    "yaml": "pyyaml",
    "Crypto": "pycryptodome",
    "Bio": "biopython",
    "dateutil": "python-dateutil",
    "pkg_resources": "setuptools",
    "zmq": "pyzmq",
    "IPython": "ipython",
    "ipykernel": "ipykernel",
    "traitlets": "traitlets",
    "jupyter_core": "jupyter_core",
    "jupyter_client": "jupyter_client",
    "nbconvert": "nbconvert",
    "nbformat": "nbformat",
    "widgetsnbextension": "widgetsnbextension",
    "skimage": "scikit-image",
    "pandas_datareader": "pandas-datareader",
    "typing_extensions": "typing-extensions",
    "sentence_transformers": "sentence-transformers",
    "mpl_toolkits": "matplotlib",
    "lxml.etree": "lxml",
    "ujson": "ujson",
    "pyarrow": "pyarrow",
    "pyproj": "pyproj",
    "shapely.geometry": "shapely",
    "osgeo": "gdal",
    "netCDF4": "netcdf4",
    "h5netcdf": "h5netcdf",
    "pydantic_core": "pydantic-core",
    "pymc3": "pymc3",
    "pymc": "pymc",
    "xarray.core": "xarray",
    "cartopy.crs": "cartopy",
    "geopandas.tools": "geopandas",
    "pygeos.lib": "pygeos",
    "fiona.collection": "fiona",
    "rasterio.plot": "rasterio",
    "pyogrio": "pyogrio",
    "vtkmodules": "vtk",
    "OpenGL.GL": "pyopengl",
    "OpenGL_accelerate": "pyopengl-accelerate",
    "PyQt5": "pyqt",
    "PyQt6": "pyqt",
    "PySide2": "pyside2",
    "PySide6": "pyside6",
    "PyQtWebEngine": "pyqtwebengine",
    "pyqtchart": "pyqtchart",
    "pyqt3d": "pyqt3d",
    "pyqt5_tools": "pyqt5-tools",
    "pyqt6_tools": "pyqt6-tools",
    "pyqt5_sip": "pyqt5-sip",
    "pyqt6_sip": "pyqt6-sip",
    "sipbuild": "sip",
    "bqplot_gl": "bqplot-gl",
    "ipyvolume.pylab": "ipyvolume",
    "k3d.plot": "k3d",
    "traittypes": "traittypes",
    "ipywebrtc": "ipywebrtc",
    "jupyterlab_widgets": "jupyterlab-widgets",
    "ipyevents": "ipyevents",
    "ipycanvas": "ipycanvas",
    "ipympl": "ipympl",
    "ipytree": "ipytree",
    "ipycytoscape": "ipycytoscape",
    "ipysheet": "ipysheet",
    "nbdime.diffing": "nbdime",
    "nbgitpuller": "nbgitpuller",
    "jupyter_server": "jupyter_server",
    "jupyterlab_server": "jupyterlab_server",
    "voila_gridstack": "voila-gridstack",
    "voila_material": "voila-material",
    "voila_vuetify": "voila-vuetify",
    "bqplot_image_gl": "bqplot-image-gl",
    "dash_bootstrap_components": "dash-bootstrap-components",
    "dash_core_components": "dash-core-components",
    "dash_html_components": "dash-html-components",
    "dash_table": "dash-table",
    "plotly.graph_objects": "plotly",
    "altair.vegalite.v4": "altair",
    "seaborn.axisgrid": "seaborn",
    "statsmodels.api": "statsmodels",
    "line_profiler": "line_profiler",
    "memory_profiler": "memory_profiler",
    "snakeviz": "snakeviz",
    "tensorboardX": "tensorboardx",
    "tensorflow_hub": "tensorflow-hub",
    "tensorflow_datasets": "tensorflow-datasets",
    "tf_agents": "tf-agents",
    "jaxlib.pocketfft": "jaxlib",
    "jax.numpy": "jax",
    "flax.linen": "flax",
    "optax": "optax",
    "chex": "chex",
    "haiku": "dm-haiku",
    "transformers.modeling_utils": "transformers",
    "datasets.load": "datasets",
    "evaluate.metrics": "evaluate",
    "accelerate.state": "accelerate",
    "scvi": "scvi-tools",
    "anndata._core": "anndata",
    "scanpy.tools": "scanpy",
    "muon._core": "muon"
}


def get_notebook_dependencies(filename: Path) -> list:

    with open(filename) as ff:
        nb = nbformat.read(ff, nbformat.NO_CONVERT)

    modules = []
    for cell in nb['cells']:

        if cell['cell_type'] == 'code':
            if not cell['source'].strip() or cell['source'].startswith('%'):
                continue
        for line in cell['source'].split('\n'):
            line = line.strip()
            if line.startswith('#'):
                continue
            words = re.split(r'(?<!,)\s+(?!,)', line)
            if len(words) >= 2:
                if words[0] == 'from':                    
                    modules.append(words[1].split('.')[0])
                elif words[0] == 'import':
                    if ',' not in words[1]:
                        modules.append(words[1].split('.')[0])
                    else:
                        for x in re.split(r'\s*,\s*', line):
                            if x:
                                modules.append(x.split('.')[0])
    dependencies = []
    for m in modules:
        if m not in sys.stdlib_module_names and not m.startswith('_'):
            dependencies.append(module_to_conda_package.get(m, m))

    return dependencies


if __name__ == '__main__':

    # read arguments from command line
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description='Update pixi dependencies from Jupyter notebooks.')
    parser.add_argument('--revalidate', action='store_true', help='Revalidate dependencies.')
    parser.add_argument('--feature', type=str, default='prod', help='The feature to add dependencies to.')
    parser.add_argument('--platform', type=str, default='linux-64', help='The platform to add dependencies for.')
    parser.add_argument('--dryrun', '-n', action='store_true', help='Only print dependencies found.')
    parser.add_argument('root', type=Path, help='The root dir with notebooks.')
    args = parser.parse_args()
    assert args.root.is_dir(), f"Root directory {args.root} does not exist or is not a directory."

    cmd = "pixi list --platform linux-64 --environment prod"
    p = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        print(f"Error running command: {cmd}")
        print(p.stderr.decode('utf-8'))
        sys.exit(1)
    data = p.stdout.decode('utf-8')
    packages_installed = {}
    for i, line in enumerate(data.splitlines()):
        if i < 2:
            continue
        package, version, build, size, scale, kind, source = line.strip().split()
        packages_installed[package] = version

    print()
    print('Scanning notebooks:')
    print()
    dependencies = []
    for path in args.root.glob('**/*.ipynb'):
        print(f'{path.name}:')
        deps_found = get_notebook_dependencies(path)
        for dep in deps_found:
            if dep in packages_installed:
                print(f"  - {dep} {packages_installed[dep]}")
            else:
                print(f"  - {dep} (missing from pixi environment)")
                dependencies.append(dep)
        # dependencies.extend(deps_found)
    dependencies = list(set(dependencies))  # remove duplicates

    print()
    if dependencies:
        print(f"Adding packages to pixi.toml")
        for dep in dependencies:
            print(f"  - {dep}")
    else:
        print("No new dependencies found.")
    print()
    if args.dryrun or not dependencies:
        sys.exit(0)

    cmd = f"pixi add --feature {args.feature} --platform {args.platform} {'--revalidate' if args.revalidate else ''} " + ' '.join(dependencies)
    cmd = shlex.split(cmd)
    cmd[0] = shutil.which(cmd[0])
    subprocess.run(cmd, check=True)
    