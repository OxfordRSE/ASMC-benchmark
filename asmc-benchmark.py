import os
import re
import sqlite3
import subprocess
import time
import datetime

import matplotlib.pyplot as plt
import pandas as pd

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
    assert os.path.isfile(haps_file + '.samples'),\
        'Expected to find haps file at {}'.format(haps_file)

    begin = time.time()

    output = subprocess.check_output([
        asmc_exe,
        '--decodingQuantFile', decoding_file,
        '--hapsFileRoot', haps_file,
        '--posteriorSums',
    ]).decode()

    # The total time for the entire subprocess
    time_total = time.time() - begin

    """
    Get some timing info out of the ASMC script output
    """
    m_read_decoding_info = re.search(
        r'Read precomputed decoding info in\s+(\d+\.?\d+)\s+seconds',
        output
    )

    time_read_dec = None
    if m_read_decoding_info is not None:
        time_read_dec = float(m_read_decoding_info.group(1))

    m_read_haps = re.search(
        r'Read haps in\s+(\d+\.?\d+)\s+seconds',
        output
    )

    time_read_haps = None
    if m_read_haps is not None:
        time_read_haps = float(m_read_haps.group(1))

    m_decode_pairs = re.search(
        r'Decoded\s+\d+\s+pairs in\s+(\d+\.?\d+)\s+seconds',
        output
    )

    time_decode = None
    if m_decode_pairs is not None:
        time_decode = float(m_decode_pairs.group(1))

    return time_total, time_read_dec, time_read_haps, time_decode


def connect_to_database(database):
    """
    Establishes a connection to a test results database.
    :param database: A path to an asmc test results database.
    :return: An open sqlite3 connection to the database.
    """
    connection = sqlite3.connect(database, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_database_schema(connection):
    """
    Given a connection to a sqlite3 database, create a table (if needed)
    containing the appropriate columns for the benchmarking results.
    """
    query = """ create table if not exists benchmarking_results(
    identifier integer primary key asc,
    date_run date,
    asmc_commit varchar,
    time_total real,
    time_read_dec real,
    time_read_haps real,
    time_decode_pairs real
    )"""
    connection.execute(query)
    connection.commit()


class ResultsDatabaseSchemaClient:
    """
    Abstract parent for database readers and writers, keeping track of the
    database columns and how to interpret the JSON column.
    """
    primary_columns = ['identifier']
    columns = [
        'date_run',
        'asmc_commit',
        'time_total',
        'time_read_dec',
        'time_read_haps',
        'time_decode_pairs',
    ]


class ResultsDatabaseWriter(ResultsDatabaseSchemaClient):
    """
    Provides write access to a SQLite3 database containing test results.
    For compatibility with the interfaces supplied by
    ResultsWriter/ResultsReader, the flat-file equivalents, instances of this
    class accept a test name and date, and provide access to the values in a
    row matching. However, due to adding multiprocessing support, test name
    and date no longer uniquely identify a test invocation so a separate
    integer counter is used as the primary key.

    This class is a Context Manager, so use it in a with block:

    >>> with ResultsDatabaseWriter("database.db") as w:
    ...     w[status] = "pending"
    """

    def __init__(self, filename, existing_row_id=None):
        self._connection = None
        self._filename = filename
        self._date = datetime.datetime.now().isoformat()
        self.__ensure_schema()
        if existing_row_id is not None:
            self._row = existing_row_id
        else:
            self.__ensure_row_exists()

    def __enter__(self):
        self._connection = connect_to_database(self._filename)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._connection.close()

    def __ensure_schema(self):
        """
        Establish that a test_results table exists, and if it didn't before,
        that it has the correct schema. Note that this method uses a temporary
        connection so it can be called outside the Context Manager lifecycle.
        :return: None.
        """
        conn = connect_to_database(self._filename)
        _ensure_database_schema(conn)
        conn.commit()
        conn.close()

    def __ensure_row_exists(self):
        """
        Create a row in the table to represent the current result, and store
        its primary key.
        Note that this method uses a temporary connection so it can be called
        outside of the Context Manager lifecycle.
        :return: None
        """
        # ensure the row exists
        conn = connect_to_database(self._filename)

        # conn.execute(
        #     'insert into test_results(name,date) values (?,?)',
        #     (self._name, self._date))

        conn.execute(
            'insert into benchmarking_results(date_run) values (?)', (self._date,)
        )
        row_id = conn.execute('select last_insert_rowid()')
        self._row = row_id.fetchone()[0]
        conn.commit()
        conn.close()

    def row_id(self):
        """
        Return the primary key for this writer's table row. Mostly for
        debugging.
        """
        return self._row

    def __setitem__(self, key, value):
        if key in self.primary_columns:
            # don't update these
            pass
        elif key in self.columns:
            self._connection.execute(
                f'update benchmarking_results set {key} = ? where identifier = ?',
                (value, self._row))
            self._connection.commit()
        else:
            pass


def get_axis_label(git_rev):
    """ Format the axis label git revision """
    return git_rev[0:7]


def get_git_url(git_rev):
    """ Determine the github url needed for the x-axis labels """
    return 'https://github.com/OxfordRSE/ASMC/commit/{}'.format(git_rev)


def plot(field, axis_label):
    """ Plot the runtime of the benchmark example """

    # Grab all the data from the SQL database
    sql_df = pd.read_sql(
        r'SELECT * from benchmarking_results',
        con=connect_to_database('asmc-benchmark.db'),
        index_col='identifier'
    )

    # Group by commit, turn off sorting to preserve git revision order
    # and subset just by the field we're interested in
    df = sql_df.groupby(
        'asmc_commit', sort=False
    ).describe()[field].reset_index()

    # Params for formatting the graph
    line_gray = '0.75'  # mid gray lines
    bg_gray = '0.9'  # light gray background
    l_blue = '#0072bd'  # light blue

    plt.rc('font', family='monospace')
    plt.rc('axes', linewidth=0.5, edgecolor=line_gray, axisbelow=True)
    plt.rc('xtick', labelsize=10)
    plt.rc('ytick', labelsize=10)
    plt.rc('xtick.major', size=0, pad=4)
    plt.rc('ytick.major', size=0, pad=4)

    plt.clf()
    plt.figure(
        figsize=(
            max(8., (len(df) / 30.0) * 20.48 / 2.0),
            8.58 / 2.0),
    )

    # x-labels will be formatted git hashes, with GitHub URLs
    x_data = range(len(df))  # Spoof x-vals as (1,2,...) for spacing labels
    x_ticks = [get_axis_label(t) for t in df['asmc_commit']]
    git_urls = [get_git_url(t) for t in df['asmc_commit']]

    # The main plot
    plt.errorbar(
        x=x_data,
        y=df['mean'], yerr=df['std'],
        fmt='o-',
        ecolor=l_blue, elinewidth=2,
        capsize=4, capthick=2
    )

    # apply GitHub URLs to x-labels
    plt.xticks(ticks=x_data, labels=x_ticks, rotation='vertical')
    locations, labels = plt.xticks()
    for url, label in zip(git_urls, labels):
        label.set_url(url)

    # y-padding is a multiple of the maximum standard deviation
    padding = 3.0 * df['std'].max()
    plt.ylim(
        (df['min'].min() - padding, df['max'].max() + padding)
    )

    plt.title("Generated by ASMC-benchmark ({:%d-%b-%Y %H:%M})".format(
        datetime.datetime.now()), fontsize=14, y=1.05)

    plt.xlabel(r'ASMC git revision', fontsize=12, labelpad=20)
    plt.ylabel(axis_label, fontsize=12, labelpad=20)

    # Alter the grid lines to be there, but subtle
    ax = plt.gca()
    ax.grid(b=True, which='major', color=line_gray, linestyle='dotted',
            dash_capstyle='round')

    # Render and save the figure as an svg
    plt.savefig('{}.svg'.format(field), bbox_inches='tight', facecolor=bg_gray,
                format='svg')
    plt.close()


if __name__ == "__main__":

    t_total, t_read_dec, t_read_haps, t_decode = benchmark_example()

    with ResultsDatabaseWriter("asmc-benchmark.db") as w:
        w['asmc_commit'] = get_asmc_git_revision()
        w['time_total'] = t_total
        w['time_read_dec'] = t_read_dec
        w['time_read_haps'] = t_read_haps
        w['time_decode_pairs'] = t_decode

    plot('time_total', 'Total execution time (s)')
    plot('time_read_dec', 'Time reading decoding info (s)')
    plot('time_read_haps', 'Time reading haps (s)')
    plot('time_decode_pairs', 'Time decoding pairs (s)')


