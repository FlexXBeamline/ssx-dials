from setuptools import setup

setup(
    name='ssx-dials',
    packages=["ssx_dials"],
    version='0.0.3',
    description='DIALS command-line tools for serial oscillation crystallography data',
    author='Steve P. Meisburger',
    author_email='spm82@cornell.edu',
    url='https://github.com/FlexXBeamline/ssx-dials',
    license='BSD',
    python_requires=">=3.10",
    install_requires=[
        "dials",
    ],
    entry_points={
        'console_scripts':[
            'ssx.import=ssx_dials.import_sliced:run',
            'ssx.find_hits=ssx_dials.find_hits:run',
            'ssx.filter_dose=ssx_dials.filter_dose:run',
            'ssx.combine=ssx_dials.combine:run',
        ],
        'libtbx.dispatcher.script':[
            'ssx.import=ssx.import',
            'ssx.find_hits=ssx.find_hits',
            'ssx.filter_dose=ssx.filter_dose',
            'ssx.combine=ssx.combine',
        ],
        "libtbx.precommit": ["ssx_dials=ssx_dials"], # necessary?
    },
    include_package_data=True,
)