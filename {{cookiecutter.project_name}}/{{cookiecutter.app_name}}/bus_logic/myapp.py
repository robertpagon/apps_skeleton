from my_app.commons import common, consts

import sys
import os, time
from collections import defaultdict
from datetime import datetime
import logging, traceback, anyconfig, glob
from docopt import docopt
import re, json
# import paramiko
import zipfile

HOME_DIR_OBRADE = os.path.dirname(os.path.realpath(__file__))
THIS_SCRIPT = os.path.basename(__file__)
TAB = ' ' * 3
logfile = common.init(THIS_SCRIPT)
# paramiko.util.log_to_file(logfile, level = "INFO")


'''
    Obrada command-line parametara
'''
# args = docopt(__doc__)
# CONFIG_FILE = args['<config_file>'] if args['<config_file>'] else f"{THIS_SCRIPT.replace('.py', '.yml')}"
CONFIG_FILE = THIS_SCRIPT.replace('.py', '.yml')
CONFIG_FILE = f"{HOME_DIR_OBRADE}/{CONFIG_FILE}"
KONFA = anyconfig.load(CONFIG_FILE) if CONFIG_FILE else None
NO_DWLD = None # args['--no-dwld'] if '--no-dwld' in args else None

regex_patterns = KONFA['regex_patterns']
load_statistics_desc = KONFA['load_statistics']
LOAD_STATISTICS_SCHEMA = load_statistics_desc['schema']
LOAD_STATISTICS_TABLE = load_statistics_desc['table']
MAX_ROWS_PER_FILE = KONFA['max_rows_per_file']
MAX_ROWS_PER_FILE_WARN_PERCENT = KONFA['max_rows_per_file_warn_percent']

# Ovo kreira rekurzivne defaultdict
nested_dict = lambda: defaultdict(nested_dict)
# statistics sadrži sve statistike programa
statistics = nested_dict()

def makedirs(source_dir):
    os.makedirs(f"{source_dir}/INPUT")
    os.makedirs(f"{source_dir}/WORKING")
    os.makedirs(f"{source_dir}/DUPLICATE")
    os.makedirs(f"{source_dir}/ARCHIVE")
    os.makedirs(f"{source_dir}/ERROR")

def get_config(source, key):
    ''' Pročitaj iz konfiguracije hijerarhijski.
        source - Konfiguracija
        key    - Može i ne mora biti lista.
                 Ovdje će postati lista.
        Primjer:
            get_config('piano', 'time_formats')
            get_config('piano', ['db_connection', 'host'])
    '''
    return common.get_config_hierarhically(KONFA, [], ['sources', source], key)

def prune_zip_extension(filename):
    for extension in ['.gz', '.zip']:
        if filename.endswith('.gz'):
            filename = filename[:-len(extension)]
    return filename

def unzip_when_necessary(source, filename, working_dir, error_dir):
    global statistics
    if filename.endswith('.gz') or filename.endswith('.zip'):
        if filename.endswith('.gz'):
            filename_unzipped = filename[:-3]
            command = f"gunzip -k {filename}"
        elif filename.endswith('.zip'):
            with zipfile.ZipFile(filename, mode="r") as archive:
               for file_in_zip in archive.namelist():
                   pass  # Učitali smo prvi fajl u arhivi, ostale fajlove (ako postoje) ignoriramo
            filename_unzipped = file_in_zip.split('/')[1]
            command = f"unzip -j {filename} {file_in_zip}"

        if os.path.isfile(filename_unzipped):
            os.remove(filename_unzipped)
        try:
            output = common.run_linux_cmd(command)
        except Exception as e:
            stacktrace = traceback.format_exc()
            message = f"Neuspjelo unzip-anje datoteke {filename}. {str(e)}"
            logging.error(f"{message}\n{stacktrace}")
            statistics['errors'].append({
                'message': message,
                'stacktrace': stacktrace,
            })
            logging.info(f'Muvam fajl {filename} u ERROR dir')
            common.move_file(filename, working_dir, error_dir)
            return None
    else:
        # Ako nije zipani fajl
        filename_unzipped = filename
    
    return filename_unzipped

def run_psql(source, sql_command):
    host = get_config(source, ['db_connection', 'host'])
    port = get_config(source, ['db_connection', 'port'])
    db = get_config(source, ['db_connection', 'db'])
    user = get_config(source, ['db_connection', 'user'])
    command = f"""psql -h {host} -p {port} -d {db} -U {user} -c "{sql_command}" """
    output = common.run_linux_cmd(command)
    return output

def insert_load_statistics(filename_unzipped, source, start_time, table_name, csv_rows_count, rows, status, status_msg):
    duration_s = round((datetime.now()-start_time).total_seconds())
    # Format datuma: '2024-06-12 15:55:06'
    sql_command = f"INSERT INTO {LOAD_STATISTICS_SCHEMA}.{LOAD_STATISTICS_TABLE} (start_time, filename, tablename, duration_s, csv_rows_count, loaded_count, status, status_msg) VALUES('{start_time.strftime('%Y-%m-%d %H:%M:%S')}', '{filename_unzipped}', '{table_name}', {duration_s}, {csv_rows_count}, {rows}, '{status}', '{status_msg}');"
    output = run_psql(source, sql_command)
    # rows = int(output[0].replace('COPY ', ''))
    logging.info(f'insert_load_statistics: {sql_command[sql_command.find("VALUES"):]}')

def load_csv_to_db(source, filename_desc, working_dir, filename, filename_unzipped):
    global statistics
    start_time = datetime.now()
    # Odredi u koju tablicu treba loadati podatke
    targeted_tables = get_config(source, ['targeted_tables'])
    # Loadanje
    table_name = targeted_tables[filename_desc['NAME']]
    csv_delimiter = get_config(source, ['csv_delimiter'])

    # Broj redaka u CSV datoteci
    output = common.run_linux_cmd(f"wc -l < {working_dir}/{filename_unzipped}")
    # print(f"filename_desc={filename_desc}")
    csv_rows_count = int(output[0])
    
    # Ovo zapravo ne treba biti vezano za source, može biti direktno ispod 'files'
    # statistics['files'][filename]['csv_rows_count'] = csv_rows_count
    statistics['sources'][source]['files'][filename]['csv_rows_count'] = csv_rows_count
    
    if csv_rows_count >= MAX_ROWS_PER_FILE:
        message = f"Neuspjelo loadanje: Tablica {table_name} ima {csv_rows_count} redaka (granični broj redaka je {MAX_ROWS_PER_FILE})"
        logging.error(message)
        statistics['errors'].append({'message': message})
    else:
        if csv_rows_count >= MAX_ROWS_PER_FILE_WARN_PERCENT * MAX_ROWS_PER_FILE // 100:
            message = f"Tablica {table_name} ima {csv_rows_count} redaka, što je više od {MAX_ROWS_PER_FILE_WARN_PERCENT}% od graničnog broja redaka ({MAX_ROWS_PER_FILE})"
            logging.warning(message)
            statistics['warnings'].append({'message': message})
        try:
            sql_command = f"\copy {table_name} FROM '{working_dir}/{filename_unzipped}' delimiters '{csv_delimiter}' CSV HEADER;"
            output = run_psql(source, sql_command)
            rows = int(output[0].replace('COPY ', ''))
            logging.info(f'Loadano je {rows} redaka u tablicu {table_name.upper()}')
            statistics['sources'][source]['files'][filename]['loaded_count'] = rows
        except Exception as e:
            message = f"Neuspjelo loadanje. {type(e).__name__} {e} "
            insert_load_statistics(filename, source, start_time, table_name, csv_rows_count, 0, 'ERROR', message)
            raise e
        else:
            insert_load_statistics(filename, source, start_time, table_name, csv_rows_count, rows, 'OK', 'OK')


def get_time_from_filename(desc):
    ''' Iz imena datoteke izvlači datumska i vremenska polja i formira string koji se može sortirati
        Npr. YYYY-MM-DD ili YYMMDD_HHMI
    '''
    time = desc.get('DATE') or desc.get('DATE_TIME')
    if 'TIME_FROM' in desc:
        time = f"{time}_desc['TIME_FROM']"
    return time

def send_mail(primatelj, body, subject, to=None):
    email_from = primatelj['from']
    email_to = to.split(',') if to else primatelj['to'].split(',')
    email_cc = primatelj['cc'].split(',') if 'cc' in primatelj else []
    additional_headers = {'BCC': primatelj['bcc']} if 'bcc' in primatelj else {}

    poruka = f"""Šaljem mail na:
    email_from={email_from}
    email_to={email_to}"
    subject={subject}"
    body={body}"
    additional_headers={additional_headers}
    consts.PODVUCI
    """
    logging.debug(poruka)

    common.send_email(email_from, email_to, cc=email_cc, subject=subject, body=body, additional_headers=additional_headers, smtp_connection=None, attachments=None)

# def send_alarm():
    # primatelj = KONFA['operaters']
    # body = primatelj['stats_body']\
        # .replace('<JOB_DURATION_M>', job_duration_m)\
        # .replace('<JOB_DURATION_S>', job_duration_m)\
        # .replace('<FILE_COUNT_PER_SOURCE>', file_count_per_source)\
        # .replace('<ROWS_COUNT_PER_FILE>', rows_count_per_file)
    # subject = primatelj['stats_subject']
    # send_mail(primatelj, body, subject)

def process_files():
    '''
      Za sve fajlove u INPUT:
        znači, možda i neke otprije koji nisu obrađeni!
      1. Muvamo u WORKING.
      2. Odzipamo ako je zipan.
      3. Loadamo u bazu.
    '''
    root_dir = f"{consts.ROOT_DIR}"
    
    # Dohvati sve iz svih INPUT i ARCHIVE direktorija
    filepaths_in_input_dir = glob.glob(f"{root_dir}/sources/**/INPUT/*", recursive=True)
    files_in_archive_dir = glob.glob(f"{root_dir}/sources/**/ARCHIVE/*", recursive=True)
    # Ali samo fajlove, ne direktorije
    filepaths_in_input_dir = [f for f in filepaths_in_input_dir if os.path.isfile(f)]
    files_in_archive_dir = [prune_zip_extension(os.path.basename(f)) for f in files_in_archive_dir if os.path.isfile(f)]

    # Razumijevanje naziva fajla
    filenames_with_desc = get_filename_semantic(filepaths_in_input_dir)
    
    # Sortiranje liste fajlova po datumu i vremenu TODO
    # filepaths_in_input_dir.sort(key=lambda filepath: get_time_from_filename(filenames_with_desc[os.path.basename(filepath)]['NAME']))
    
    for filepath in filepaths_in_input_dir:
        filename = os.path.basename(filepath)
        filename_desc = filenames_with_desc[filename]

        source = filename_desc['source']
        input_dir = f"{root_dir}/sources/{source}/INPUT"
        working_dir = f"{root_dir}/sources/{source}/WORKING"
        duplicate_dir = f"{root_dir}/sources/{source}/DUPLICATE"
        archive_dir = f"{root_dir}/sources/{source}/ARCHIVE"
        error_dir = f"{root_dir}/sources/{source}/ERROR"

        filesize = os.path.getsize(filepath)
        logging.info(f'U INPUT direktoriju se nalazi datoteka {filename} veličine {filesize} bajtova')
        
        # 1. Muvamo u WORKING.
        logging.info(f'Muvam fajl {filename} u WORKING dir')
        common.move_file(filename, input_dir, working_dir)

        # 2. Ako je istoimena datoteka u ARCHIVE, onda nećemo ponavljati loadanje, nego muvati u direktorij DUPLICATE
        if prune_zip_extension(filename) in files_in_archive_dir:
            message = f'Datoteka {filename} je već otprije učitana u bazu, pa je premještam u direktorij DUPLICATE.'
            logging.info(message)
            statistics['warnings'].append({'message': message})
            common.move_file(filename, working_dir, duplicate_dir)
            continue

        # 2. Odzipamo ako treba
        os.chdir(working_dir)
        filename_unzipped = unzip_when_necessary(source, filename, working_dir, error_dir)
        if not filename_unzipped:
            # Ako nije dojavljeno ime fajla, onda znači da je u funkciji obrađena greška i treba ići na sljedeću datoteku
            continue

        try:
            # 3a. Loadamo u bazu.
            load_csv_to_db(source, filename_desc, working_dir, filename, filename_unzipped)
        except Exception as e:
            stacktrace = traceback.format_exc()
            message = f"Neuspjelo loadanje {filename_unzipped} u bazu. {str(e)}"
            logging.error(f"{message}\n{stacktrace}")
            statistics['errors'].append({
                'message': message,
                'stacktrace': stacktrace,
            })
            logging.info(f'Muvam fajl {filename} u ERROR dir')
            common.move_file(filename, working_dir, error_dir)
            continue

        # 5. Muvamo original u ARCHIVE.
        logging.info(f'Muvam fajl {filename} u ARCHIVE dir')
        common.move_file(filename, working_dir, archive_dir)
        if filename_unzipped != filename:
            # Ovo je slučaj kad smo trebali raspakirati, pa zato sad trebamo obrisati obje datoteke
            os.remove(filename_unzipped)
            logging.info(f'Obrisana raspakirana datoteka {filename_unzipped} u WORKING dir')
        
def recognize_source_from_filename(filename):
    return filename.split('_')[0]

def get_regex_pattern(filename_patern):
    ''' Napravi regex kojim ćemo pročitati originalno ime datoteke koju nađemo na sFTP serveru.
    '''
    regex_pattern = filename_patern
    result = re.finditer('\[(\w+)\]', filename_patern)
    parts = []
    for match_obj in result:
        part = match_obj.group(1)
        parts.append(part)
        regex_pattern = regex_pattern.replace(f"[{part}]", f"({regex_patterns[part]})")
    regex_pattern = regex_pattern.replace('.','\.')
    return regex_pattern, parts

def get_filename_semantic(filepath_list):
    ''' Analiziraj ime svake datoteke iz liste.
        Ako prepoznaješ filename, onda pridruži značenja definiranim dijelovima naziva datoteke.
        Cijelu analizu vrati u obliku:
        { <filename_bez_zip>: { "NAME": "<ime_reporta_1>", ..., "ZIP": '.gz' } 
          <filename_bez_zip>: { "NAME": "<ime_reporta_2>", ..., "ZIP": None } 
        }
        Ako NE prepoznaješ filename ni po jednom filename patternu, takve izgnoriraj.
    '''
    filenames_with_desc = {}
    for filepath in filepath_list:

        filename = os.path.basename(filepath)
        
        # Izvadi naziv sourcea
        source = recognize_source_from_filename(filename)
        
        # Za taj source pročitaj moguće file name patterns
        filename_paterns = get_config(source, 'filenames')
        
        # Pronađi odgovara li ime fajla nekom patternu i prema njemu iščitaj ime fajla
        pattern_is_found = False
        for filename_patern_dict in filename_paterns or []:
            # npr. filename_patern_dict = 'offerista_[NAME]_[DATE_TIME]_[IGNORE].[EXT]: 10'
            filename_patern = list(filename_patern_dict.keys())[0]
            # npr. filename_patern = 'offerista_[NAME]_[DATE_TIME]_[IGNORE].[EXT]'
            
            regex_pattern, parts = get_regex_pattern(filename_patern)
            
            #
            # Analiziraj ime fajla
            #
            match = re.fullmatch(regex_pattern, filename)
            if match:
                file_desc = filenames_with_desc[filename] = { 'source': source }
                for i in range(len(parts)):
                    file_desc[parts[i]] = match.group(i+1)
                pattern_is_found = True
                break  # Nađen je odgovarajući pattern, ne treba više tražiti

        if not pattern_is_found:
            logging.error(f"Za datoteku {filename} nije pronađen odgovarajući file name pattern!")
    
    return filenames_with_desc

def is_recognized(filename, filename_paterns):
    # Pronađi odgovara li ime fajla nekom patternu i prema njemu iščitaj ime fajla
    pattern_is_found = None
    for filename_patern in filename_paterns or []:
        # npr. filename_patern = 'offerista_[NAME]_[DATE_TIME]_[IGNORE].[EXT]'
        regex_pattern, parts = get_regex_pattern(filename_patern)
        match = re.fullmatch(regex_pattern, filename)
        if match:
            pattern_is_found = filename_patern
            break  # Nađen je odgovarajući pattern, ne treba više tražiti
    return pattern_is_found

def dwld_files_from_sftp():

    # Otvori konekciju prema sftp serveru
    transport, sftp = sftp_connect()
    
    # 1. Kojih fajlova ima na serveru?
    fajls_on_sftp = sftp.listdir(consts.SFTP_UPLOAD_DIR)
    
    # Skupi filename patterne
    filename_paterns_desc = {}
    for source in KONFA['sources']:
        source_filename_paterns = get_config(source, 'filenames')
        for filename_patern_dict in source_filename_paterns:
            filename_paterns_desc = filename_paterns_desc | filename_patern_dict
    filename_paterns = set(filename_paterns_desc.keys())

    # Prepoznaj fajlove
    recognized_files = []
    for filename in fajls_on_sftp:
        filename_patern = is_recognized(filename, filename_paterns)
        if filename_patern:
            recognized_files.append(filename)
            # print(f"FILENAME_PATERNS_DESC={filename_paterns_desc}")
            if not 'file_cnt' in filename_paterns_desc[filename_patern]:
                filename_paterns_desc[filename_patern]['file_cnt'] = 1
            else:
                filename_paterns_desc[filename_patern]['file_cnt'] += 1
    for pattern in filename_paterns_desc:
        pattern_desc = filename_paterns_desc[pattern]
        if pattern_desc and 'expected_cnt' in pattern_desc and pattern_desc['expected_cnt'] and pattern_desc.get('file_cnt') != pattern_desc['expected_cnt']:
            message = f"Očekuje se da za file name pattern {pattern} stigne {pattern_desc['expected_cnt']} datoteka, ali stiglo je {pattern_desc['file_cnt']} datoteka"
            statistics['warnings'].append({'message': message})

    # 3. Download fajlova
    move_from_sftp(sftp, recognized_files)
    
    # Zatvori konekciju prema sftp serveru
    sftp_disconnect(sftp, transport)

def get_statistics_messages(subject, message_type, sifra, cega):
    messages = ''
    if statistics.get(message_type):
        # Stavi prefix "ERROR - " i/ili "WARNING - "
        subject = f"{sifra} - {subject}"
        messages = f"\n\n{cega}:\n"
        for message in statistics[message_type]:
            messages += f"{TAB}{message['message']}\n"
            # if message.get('stacktrace'):
                # messages += f"{TAB}{TAB}{message['stacktrace']}\n"
        # messages += "\n\n"
    return messages
        
def send_job_statistics():
    global statistics
    job_duration = round((statistics['job_end'] - statistics['job_start']).total_seconds())
    job_duration_m = job_duration // 60
    job_duration_s = job_duration - job_duration_m * 60

    file_count_per_source = ''
    rows_count_per_file = ''
    for source in statistics.get('sources') or []:
        source_desc = statistics['sources'][source]
        file_count_per_source += f"{TAB}{source.ljust(20)} {source_desc['file_count']}\n"
        for table_name in source_desc.get('files') or []:
            table_desc = source_desc['files'][table_name]
            rows_count_per_file += f"{TAB}{table_name.ljust(60)} {str(table_desc['csv_rows_count']).rjust(15)}\n"
            #  {str(table_desc.get('loaded_count')).rjust(15)}

    primatelj = KONFA['operaters']
    subject = primatelj['stats_subject']
    warnings = get_statistics_messages(subject, 'warnings', 'WARN', 'Upozorenja')
    errors = get_statistics_messages(subject, 'errors', 'ERROR', 'Greške')
        
    body = primatelj['stats_body']\
        .replace('<ERRORS>', errors)\
        .replace('<WARNINGS>', warnings)\
        .replace('<JOB_DURATION_M>', str(job_duration_m).rjust(2, '0'))\
        .replace('<JOB_DURATION_S>', str(job_duration_s).rjust(2, '0'))\
        .replace('<FILE_COUNT_PER_SOURCE>', str(file_count_per_source))\
        .replace('<ROWS_COUNT_PER_FILE>', str(rows_count_per_file))
    send_mail(primatelj, body, subject)


if __name__ == '__main__':
    
    statistics['job_start'] = datetime.now()
    statistics['errors'] = []
    statistics['warnings'] = []
    
    try:
        
        if not NO_DWLD:
            dwld_files_from_sftp()
        
        # Obradi fajlove
        process_files()

    except Exception as e:
        stacktrace = traceback.format_exc()
        message = f"Neočekivani prekid obrade. {str(e)}"
        logging.critical(f"{message}\n{stacktrace}")
        statistics['errors'].append({
            'message': message,
            'stacktrace': stacktrace,
        })
    finally:
        statistics['job_end'] = datetime.now()
        try:
            send_job_statistics()
        except Exception as e:
            stacktrace = traceback.format_exc()
            message = f"Neuspjelo slanje maila s izvještajem o izvršenoj obradi. {str(e)}"
            logging.critical(f"{message}\n{stacktrace}")

# print(f"OUTPUT={output}")
