from datetime import datetime

from create_tables import create_database, main_tables, data_tables,\
    events_tables
from extractor import QuandlCodeExtract, QuandlDataExtraction,\
    GoogleFinanceDataExtraction, YahooFinanceDataExtraction, CSIDataExtractor
from load_aux_tables import LoadTables
from build_symbology import create_symbology
from cross_validator import CrossValidate
from utilities.database_queries import query_all_active_tsids
from utilities.user_dir import user_dir

__author__ = 'Josh Schertz'
__copyright__ = 'Copyright (C) 2016 Josh Schertz'
__description__ = 'An automated system to store and maintain financial data.'
__email__ = 'josh[AT]joshschertz[DOT]com'
__license__ = 'GNU AGPLv3'
__maintainer__ = 'Josh Schertz'
__status__ = 'Development'
__url__ = 'https://joshschertz.com/'
__version__ = '1.3.2'

'''
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

''' pySecMaster.py

This manages the securities master database. It can be run daily.

Database maintenance tasks:
    Creates the tables in the database.
    Loads auxiliary tables from included CSV files.
    Downloads all available Quandl Codes for the Quandl Databases selected.
    Downloads the specified CSI Data factsheet (stocks, commodities).
    Creates the symbology table which establishes a unique code for every
        item in the database, along with translating different source's codes

Database data download tasks:
    Downloads Quandl data based on the download selection criteria using either
        the official Quandl Codes or implied codes from CSI Data.
    Downloads Google Finance minute stock data.
    Can either append only the new data, or replace part of the existing data.

Future expansions:
    Implement daily option chain data (from Google or Yahoo).
'''

###############################################################################
# Database maintenance options:

userdir = user_dir()

csidata_type = 'stock'      # stock, commodity

# Don't change these unless you know what you are doing
database_url = ['https://www.quandl.com/api/v2/datasets.csv?query=*&'
                'source_code=', '&per_page=300&page=']
# http://www.csidata.com/factsheets.php?type=stock&format=html
csidata_url = 'http://www.csidata.com/factsheets.php?'
tables_to_load = ['data_vendor', 'exchanges']
symbology_sources = ['csi_data', 'tsid', 'quandl_wiki', 'quandl_goog',
                     'seeking_alpha', 'yahoo']

###############################################################################
# Database data download options:

today = datetime.today()

# Don't change these variables unless you know what you are doing!
quandl_data_url = ['https://www.quandl.com/api/v1/datasets/', '.csv']

google_fin_url = {'root': 'http://www.google.com/finance/getprices?',
                  'ticker': 'q=',
                  'exchange': 'x=',
                  'interval': 'i=',   # 60; 60 seconds is the shortest interval
                  # 'sessions': 'sessions=ext_hours',
                  'period': 'p=',    # 20d; 15d is the longest period for min
                  'fields': 'f=d,c,v,o,h,l'}    # order doesn't change anything

yahoo_end_date = ('d=%s&e=%s&f=%s' %
                  (str(int(today.month - 1)).zfill(2), today.day, today.year))
yahoo_fin_url = {'root': 'http://real-chart.finance.yahoo.com/table.csv?',
                 'ticker': 's=',    # Exchange is added after ticker and '.'
                 'interval': 'g=',  # d, w, m, v: (daily, wkly, mth, dividends)
                 'start_date': 'a=00&b=1&c=1900',   # The entire price history
                 'end_date': yahoo_end_date,    # Today's date (MM; D; YYYY)
                 'csv': 'ignore=.csv'}      # Returns a CSV file
###############################################################################


def maintenance(quandl_ticker_source, database_list, threads,
                quandl_update_range, csidata_update_range, symbology_sources):

    print('Starting Security Master table maintenance function. This can take '
          'some time to finish if large databases are used. If this fails, '
          'rerun it after a few minutes.')

    # Create the SQL tables if they don't already exist
    create_database(database=userdir['postgresql']['pysecmaster_db'],
                    user=userdir['postgresql']['pysecmaster_user'])
    main_tables(database=userdir['postgresql']['pysecmaster_db'],
                user=userdir['postgresql']['pysecmaster_user'],
                password=userdir['postgresql']['pysecmaster_password'],
                host=userdir['postgresql']['pysecmaster_host'],
                port=userdir['postgresql']['pysecmaster_port'])
    data_tables(database=userdir['postgresql']['pysecmaster_db'],
                user=userdir['postgresql']['pysecmaster_user'],
                password=userdir['postgresql']['pysecmaster_password'],
                host=userdir['postgresql']['pysecmaster_host'],
                port=userdir['postgresql']['pysecmaster_port'])
    events_tables(database=userdir['postgresql']['pysecmaster_db'],
                  user=userdir['postgresql']['pysecmaster_user'],
                  password=userdir['postgresql']['pysecmaster_password'],
                  host=userdir['postgresql']['pysecmaster_host'],
                  port=userdir['postgresql']['pysecmaster_port'])

    LoadTables(database=userdir['postgresql']['pysecmaster_db'],
               user=userdir['postgresql']['pysecmaster_user'],
               password=userdir['postgresql']['pysecmaster_password'],
               host=userdir['postgresql']['pysecmaster_host'],
               port=userdir['postgresql']['pysecmaster_port'],
               tables_to_load=tables_to_load)

    # Always extract CSI values, as they are used for the symbology table
    CSIDataExtractor(database=userdir['postgresql']['pysecmaster_db'],
                     user=userdir['postgresql']['pysecmaster_user'],
                     password=userdir['postgresql']['pysecmaster_password'],
                     host=userdir['postgresql']['pysecmaster_host'],
                     port=userdir['postgresql']['pysecmaster_port'],
                     db_url=csidata_url,
                     data_type=csidata_type,
                     redownload_time=csidata_update_range)

    if quandl_ticker_source == 'quandl':
        QuandlCodeExtract(database=userdir['postgresql']['pysecmaster_db'],
                          user=userdir['postgresql']['pysecmaster_user'],
                          password=userdir['postgresql']['pysecmaster_password'],
                          host=userdir['postgresql']['pysecmaster_host'],
                          port=userdir['postgresql']['pysecmaster_port'],
                          quandl_token=userdir['quandl']['quandl_token'],
                          database_list=database_list,
                          database_url=database_url,
                          update_range=quandl_update_range,
                          threads=threads)

    create_symbology(database=userdir['postgresql']['pysecmaster_db'],
                     user=userdir['postgresql']['pysecmaster_user'],
                     password=userdir['postgresql']['pysecmaster_password'],
                     host=userdir['postgresql']['pysecmaster_host'],
                     port=userdir['postgresql']['pysecmaster_port'],
                     source_list=symbology_sources)


def data_download(download_list, threads=4, verbose=False):
    """ Loops through all provided data sources in download_list, and runs
    the associated data extractor using the provided source variables.

    :param download_list: List of dictionaries, with each dictionary containing
        all of the relevant variables for the specific source
    :param threads: Integer indicating how many threads should be used to
        concurrently download data
    :param verbose: Boolean of whether debugging prints should occur.
    """

    for source in download_list:
        if source['interval'] == 'daily':
            table = 'daily_prices'
            if source['source'] == 'google':
                google_fin_url['interval'] = 'i=' + str(60*60*24)
            elif source['source'] == 'yahoo':
                yahoo_fin_url['interval'] = 'g=d'
        elif source['interval'] == 'minute':
            table = 'minute_prices'
            if source['source'] == 'google':
                google_fin_url['interval'] = 'i=' + str(60)
            elif source['source'] == 'yahoo':
                raise SystemError('Yahoo Finance does not provide minute data.')
        else:
            raise SystemError('No interval was provided for %s in '
                              'data_download in pySecMaster.py' %
                              source['interval'])

        if source['source'] == 'quandl':
            quandl_key = userdir['quandl']['quandl_token']
            if quandl_key:
                # Download data for selected Quandl codes
                print('\nDownloading all Quandl fields for: %s'
                      '\nNew data will %s the prior %s day\'s data' %
                      (source['selection'], source['data_process'],
                       source['replace_days_back']))
                QuandlDataExtraction(
                    database=userdir['postgresql']['pysecmaster_db'],
                    user=userdir['postgresql']['pysecmaster_user'],
                    password=userdir['postgresql']['pysecmaster_password'],
                    host=userdir['postgresql']['pysecmaster_host'],
                    port=userdir['postgresql']['pysecmaster_port'],
                    quandl_token=quandl_key,
                    db_url=quandl_data_url,
                    download_selection=source['selection'],
                    redownload_time=source['redownload_time'],
                    data_process=source['data_process'],
                    days_back=source['replace_days_back'],
                    threads=threads,
                    table=table,
                    verbose=verbose)
            else:
                print('\nNot able to download Quandl data for %s because '
                      'there was no Quandl API key provided.' %
                      (source['selection'],))

        elif source['source'] == 'google':
            # Download data for selected Google Finance codes
            print('\nDownloading all Google Finance fields for: %s'
                  '\nNew data will %s the prior %s day\'s data' %
                  (source['selection'], source['data_process'],
                   source['replace_days_back']))

            google_fin_url['period'] = 'p=' + str(source['period']) + 'd'
            GoogleFinanceDataExtraction(
                database=userdir['postgresql']['pysecmaster_db'],
                user=userdir['postgresql']['pysecmaster_user'],
                password=userdir['postgresql']['pysecmaster_password'],
                host=userdir['postgresql']['pysecmaster_host'],
                port=userdir['postgresql']['pysecmaster_port'],
                db_url=google_fin_url,
                download_selection=source['selection'],
                redownload_time=source['redownload_time'],
                data_process=source['data_process'],
                days_back=source['replace_days_back'],
                threads=threads,
                table=table,
                verbose=verbose)

        elif source['source'] == 'yahoo':
            # Download data for selected Google Finance codes
            print('\nDownloading all Yahoo Finance fields for: %s'
                  '\nNew data will %s the prior %s day\'s data' %
                  (source['selection'], source['data_process'],
                   source['replace_days_back']))

            YahooFinanceDataExtraction(
                database=userdir['postgresql']['pysecmaster_db'],
                user=userdir['postgresql']['pysecmaster_user'],
                password=userdir['postgresql']['pysecmaster_password'],
                host=userdir['postgresql']['pysecmaster_host'],
                port=userdir['postgresql']['pysecmaster_port'],
                db_url=yahoo_fin_url,
                download_selection=source['selection'],
                redownload_time=source['redownload_time'],
                data_process=source['data_process'],
                days_back=source['replace_days_back'],
                threads=threads,
                table=table,
                verbose=verbose)

        else:
            print('The %s source is currently not implemented. Skipping it.' %
                  source['source'])

    print('All available data values have been downloaded for: %s' %
          download_list)


def post_download_maintenance(download_list, period=None, verbose=False):
    """ Perform tasks that require all data to be downloaded first, such as the
    source cross validator function.

    :param download_list: List of dictionaries, with each dictionary containing
        all of the relevant variables for the specific source
    :param period: Optional integer indicating the prior number of days whose
            values should be cross validated. If None is provided, then the
            entire set of values will be validated.
    :param verbose: Boolean of whether debugging prints should occur.
    """

    table = None
    for source in download_list:
        if source['interval'] == 'daily':
            table = 'daily_prices'
        elif source['interval'] == 'minute':
            table = 'minute_prices'
        else:
            raise SystemError('No interval was provided for %s in '
                              'data_download in pySecMaster.py' %
                              source['interval'])

    tsids_df = query_all_active_tsids(
        database=userdir['postgresql']['pysecmaster_db'],
        user=userdir['postgresql']['pysecmaster_user'],
        password=userdir['postgresql']['pysecmaster_password'],
        host=userdir['postgresql']['pysecmaster_host'],
        port=userdir['postgresql']['pysecmaster_port'],
        table=table,
        period=period)
    tsid_list = tsids_df['tsid'].values

    CrossValidate(
        database=userdir['postgresql']['pysecmaster_db'],
        user=userdir['postgresql']['pysecmaster_user'],
        password=userdir['postgresql']['pysecmaster_password'],
        host=userdir['postgresql']['pysecmaster_host'],
        port=userdir['postgresql']['pysecmaster_port'],
        table=table, tsid_list=tsid_list, period=period, verbose=verbose)


if __name__ == '__main__':

    ############################################################################
    # Database maintenance options:

    # These are the Quandl Databases that will have all their codes downloaded
    # Examples: 'GOOG', 'WIKI', 'YAHOO', 'SEC', 'EIA', 'JODI', 'CURRFX', 'FINRA'
    # ToDo: Determine how to handle Futures; codes are a single item w/o a '_'
    # ToDo: Determine how to handle USDAFAS; codes have 3 item formats
    database_list = ['WIKI']

    # Integer that represents the number of days before the ticker tables will
    #   be refreshed. In addition, if a database wasn't completely downloaded
    #   within this data range, the remainder of the codes will attempt to
    #   download (relevant for Quandl codes).
    quandl_update_range = 30
    csidata_update_range = 5

    ############################################################################
    # Database data download options:

    # When the Quandl data is downloaded, where should the extractor get the
    #   ticker codes from? Either use the official list of codes from Quandl
    #   (quandl), or make implied codes from the CSI Data stock factsheet
    #   (csidata) which is more accurate but tries more non-existent companies.
    quandl_ticker_source = 'csidata'        # quandl, csidata

    # Example download list: should be a list of dictionaries, with the
    #   dictionaries containing all relevant variables for the specific source
    test_download_list = [
        {'source': 'quandl', 'selection': 'wiki', 'interval': 'daily',
         'redownload_time': 60 * 60 * 24, 'data_process': 'replace',
         'replace_days_back': 60},
        {'source': 'quandl', 'selection': 'goog_us_main_no_end_date',
         'interval': 'daily', 'redownload_time': 60 * 60 * 12,
         'data_process': 'replace', 'replace_days_back': 60},
        # {'source': 'google', 'selection': 'us_main_no_end_date',
        #  'interval': 'daily', 'period': 60, 'redownload_time': 60 * 60 * 12,
        #  'data_process': 'replace', 'replace_days_back': 60},
        {'source': 'yahoo', 'selection': 'us_main', 'interval': 'daily',
         'redownload_time': 60 * 60 * 12, 'data_process': 'replace',
         'replace_days_back': 60}
    ]
    # test_download_list = [
    #     {'source': 'google', 'selection': 'us_main', 'interval': 'minute',
    #      'period': 20, 'redownload_time': 60 * 60 * 12,
    #      'data_process': 'replace', 'replace_days_back': 10}
    # ]

    # source: String of which data provider should have their data downloaded
    # selection: String of which data from the source should be downloaded. To
    #   understand what is actually being downloaded, go to the query_q_codes
    #   method in either the QuandlDataExtraction class or the
    #   GoogleFinanceDataExtraction class in extractor.py, and look at the
    #   SQLite queries. (Quandl: 'wiki', 'goog', 'goog_us_main',
    #   'goog_us_main_no_end_date', 'goog_us_canada_london', 'goog_etf';
    #   Google: 'all', 'us_main', 'us_main_no_end_date', 'us_canada_london')
    # interval: String of what interval the data should be in (daily or minute).
    # period: Integer of how many day's data should be downloaded (Google
    #   finance only). Minute data only has data back 15 days, and daily data
    #   only has data back 50 days.
    # redownload_time: Integer representing time in seconds before the data is
    #   allowed to be re-downloaded. Allows the system to be restarted without
    #   downloading the same data again.
    # data_process: String of how the new data will interact with the existing
    #   data ('replace': replace the prior x days of data (replace_days_back);
    #   'append': append the latest data to the existing data (will ignore
    #   replace_days_back variable). 'append' requires less system resources
    #   since it only adds new values, instead of deleting overlapping values.
    # replace_days_back: Integer of the number of days whose existing data
    #   should be replaced by new data (50000 replaces all existing data). Due
    #   to weekends, the days replaced may differ depending on what day this
    #   function is run
    ############################################################################

    maintenance(quandl_ticker_source=quandl_ticker_source,
                database_list=database_list,
                threads=8,
                quandl_update_range=quandl_update_range,
                csidata_update_range=csidata_update_range,
                symbology_sources=symbology_sources)

    data_download(download_list=test_download_list,
                  threads=8,    # 3 for replace; 8 for append
                  verbose=True)

    # post_download_maintenance(download_list=test_download_list,
    #                           # period=60,
    #                           verbose=True)
    # print(datetime.now())
