import os
import subprocess

script_path = os.path.realpath(os.path.dirname(__file__))
build_dir = os.path.join(script_path, '__asmc_build')
asmc_exe = os.path.join(build_dir, 'ASMC_exe')

subprocess.call([
        asmc_exe
    ]
)
