import os
import subprocess
import time

script_dir = os.path.realpath(os.path.dirname(__file__))
build_dir = os.path.join(script_dir, '__asmc_build')
asmc_dir = os.path.join(script_dir, 'ASMC')


def get_asmc_git_revision():
    """
    Get the git hash of the ASMC version being run
    :return: ASMC git hash
    """
    return subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'],
        cwd=asmc_dir,
    ).decode().strip()


def benchmark_example():
    """
    Run the ASMC example, and return the time taken.
    :return: time taken to run the ASMC example.
    """

    asmc_exe = os.path.join(build_dir, 'ASMC_exe')
    decoding_file = os.path.join(
        asmc_dir,
        'FILES',
        'DECODING_QUANTITIES',
        '30-100-2000.decodingQuantities.gz'
    )
    haps_file = os.path.join(
        asmc_dir,
        'FILES',
        'EXAMPLE',
        'exampleFile.n300.array'
    )

    assert os.path.isfile(asmc_exe),\
        'Expected to find ASMC_exe at {}'.format(asmc_exe)
    assert os.path.isfile(decoding_file),\
        'Expected to find decoding quantities file at {}'.format(decoding_file)
    assert os.path.isfile(haps_file),\
        'Expected to find haps file at {}'.format(haps_file)

    begin = time.time()

    subprocess.call([
        asmc_exe,
        '--decodingQuantFile', decoding_file,
        '--hapsFileRoot', haps_file,
        '--posteriorSums',
    ])

    end = time.time()

    return end - begin


if __name__ == "__main__":

    print(get_asmc_git_revision())
    print(benchmark_example())
