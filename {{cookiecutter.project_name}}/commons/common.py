#!/usr/bin/python3

'''
Zajednički kod skripti
'''

import sys

import os, time
from os import path
from os.path import basename
from datetime import datetime
import logging, traceback, glob
import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import COMMASPACE
from email.mime.multipart import MIMEMultipart

from commons import consts

def init(script_name):
    '''
      Inicijalizacija logiranja
    '''
    logfile = f"{script_name}.log"
    logdir = consts.LOG_DIR
    if os.path.exists(logdir):
        logfile = f"{logdir}/{logfile}"
    logging.basicConfig(
        level=logging.INFO,
        format=consts.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(logfile)
        ]
    )
    logging.info(consts.PODVUCI)
    logging.info(f"Pokreće se program {script_name}")
    return logfile

class NeocekivanaGreska(Exception):
    pass


def run_linux_cmd(args_list):
    ''' Pokreće linux naredbe
    '''
    # logging.info(f"Pokrećem unix naredbu: {args_list}")
    proc = subprocess.Popen(args_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    s_output, s_err = proc.communicate()
    s_return =  proc.returncode
    if s_return != 0:
        error_message = f"Neuspjela naredba: {args_list}\ncode={s_return}, error={s_err.decode('utf-8')}"
        logging.error(error_message)
        raise NeocekivanaGreska(error_message)
    return s_output.decode('utf-8').split('\n')
    
            
def move_file(filename, from_dir, to_dir):
    old_path = os.path.join(from_dir, filename)
    new_path = os.path.join(to_dir, filename)
    os.rename(old_path, new_path)

def send_email(email_from, to, cc = [], subject = '', body = '', additional_headers={}, smtp_connection=None, attachments=[]):
    '''
    Slanje mailova direktno iz programa
    
    additional_headers - možeš poslati svoje drugačije headere koji će dodati nove ili pregaziti defaultne headere
    '''
    
    # Ovo je primjer za korištenje ako bi trebao TLS ili username/password
    tls = True
    tls = False

    # Makni oznake kraja retka iz naslova, za svaki slučaj
    for ill in [ "\n", "\r" ]:
        subject = subject.replace(ill, ' ')

    # Defaultni headeri
    headers = {
        'Content-Type': 'text/html; charset=utf-8',
        'Content-Disposition': 'inline',
        'Content-Transfer-Encoding': '8bit',
        'From': email_from,
        'To': COMMASPACE.join(to),
        'CC': COMMASPACE.join(cc),
        'Date': datetime.now().strftime('%a, %d %b %Y  %H:%M:%S %Z'),
        'X-Mailer': 'python',
        'Subject': subject
    }
    
    headers.update(additional_headers)

    # create the message
    message = MIMEMultipart()
    for key, value in headers.items():
        message[key] = value

    # add contents
    messageText = MIMEText(body,'plain') # html
    message.attach(messageText)
    message_wo_attachments = message.as_string()

    pocetak_slanja = int(round(time.time()))

    # Spajanje na SMTP server
    if not smtp_connection:
        try:
            logging.info(f'Spajam se na SMTP server {consts.SMTP_SERVER}:{consts.SMTP_SERVER_PORT}')
            smtp_connection = smtplib.SMTP(consts.SMTP_SERVER, consts.SMTP_SERVER_PORT)
        except Exception as e:
            raise ValueError(f"Nije uspjelo spajanje na SMTP server") from e
        try:
            # Prijava na server (ako treba)
            if tls:
                smtp_connection.ehlo()
                smtp_connection.starttls()
                smtp_connection.ehlo()
                logging.info(f'TLS pokrenut')

            # if consts.SMTP_USERNAME and consts.SMTP_PASSWORD:
                # logging.info(f'Logiram se na SMTP server')
                # smtp_connection.login(consts.SMTP_USERNAME, consts.SMTP_PASSWORD)
        except Exception as e:
            raise ConnectionError(f"Nije uspjelo TLS i/ili logiranje na SMTP server") from e

    all_receivers = to + cc if 'BCC' not in headers else to + cc + headers['BCC'].replace(' ','').split(',')

    for attachment in attachments or []:
        logging.info(f"Prilažem datoteku {attachment}")
        with open(attachment, "rb") as datoteka:
            part = MIMEApplication(
                datoteka.read(),
                Name=basename(attachment)
            )
        # After the file is closed
        part['Content-Disposition'] = 'attachment; filename="%s"' % basename(attachment)
        message.attach(part)

    # Slanje maila
    try:
        logging.info(f'Šaljem mail. Message=\n{message_wo_attachments}{consts.PODVUCI}\nZbog veličine, nisu ispisani attachmenti')
        # smtp_connection.sendmail(headers['From'], all_receivers, msg.encode("utf8"))
        smtp_connection.sendmail(headers['From'], all_receivers, message.as_string())
        # smtp_connection.quit()
        logging.info("Uspješno poslan mail")
    except Exception as e:
        raise ConnectionError(f"Nije uspjelo slanje maila") from e

    logging.info('Slanje maila je trajalo ' + str(int(round(time.time())) - pocetak_slanja) + ' sekundi' + consts.PODVUCI)
    
    # Ako netko ponovno hoće koristiti ovu konekciju, nek ponovno zatraži slanje s tom konekcijom u parametrima
    return smtp_connection
    
def send_mail(primatelj, mjesec, godina, fajlovi, smtp_connection=None, to=None):
    mj = consts.MJESECI[int(mjesec)-1]
    subject = primatelj['subject'].replace('<MJESEC>', mjesec).replace('<GODINA>', godina)
    body = primatelj['body'].replace('<MJ>', mj).replace('<GODINA>', godina)
    email_from = primatelj['from']
    email_to = to.split(',') if to else primatelj['to'].split(',')
    email_cc = primatelj['cc'].split(',') if 'cc' in primatelj else []
    additional_headers = {'BCC': primatelj['bcc']} if 'bcc' in primatelj else {}

    poruka = f"""Šaljem mail na:
    email_from={email_from}
    email_to={email_to}"
    subject={subject}"
    body={body}"
    additional_headers={additional_headers}"""
    print(poruka)
    print(consts.PODVUCI)

    common.send_email(email_from, email_to, cc=email_cc, subject=subject, body=body, additional_headers=additional_headers, smtp_connection=None, attachments=fajlovi)

def get_dict_value(dict_tree, key_list):
    ''' Daje vrijednost u stablu dictionarija.
        Ako ne nađe, vraća None.
        Primjer:
        a = {'c': 2, 'b': {'e': 3, 'd': 4}}
        print(f"rezultat={get_dict_value(a, ['b','e'])}")
    '''
    value = None
    key_list_length = len(key_list)
    if key_list_length > 0:
        first_key = key_list.pop(0)
        if first_key in dict_tree:
            if key_list_length == 1:
                value = dict_tree[first_key]
            else:
                value = get_dict_value(dict_tree[first_key], key_list)
    return value

def get_config_hierarhically(dict_tree, key_list_prefix, key_list, key):
    ''' Iz konfiguracije vraća vrijednost pod ključem key_list.
        Ako nema, onda po stablu prema korijenu traži vrijednost pod istim ključem.
        Ako ne nađe, vraća None.
        dict_tree je u obliku stabla dictionarija.
        Naime, ključevi su zadani kao liste ključeva. Npr. dict_tree['a']['b']['c']=> ['a', 'b', 'c']
        Primjer:
        dict_tree = {'c':{'f':1},'a':{'c':{'f':2},'b':{'e':3,'d':4}}}
        value = get_config_hierarhically(dict_tree, ['a'], ['b'], ['c','f'])
        2
    '''
    if not isinstance(key, list):
        key = [key]
    value = get_dict_value(dict_tree, key_list_prefix + key_list.copy() + key)
    key_list_length = len(key_list)
    if not value and key_list_length > 0:
        key_list.pop(key_list_length - 1)
        value = get_config_hierarhically(dict_tree, key_list_prefix, key_list, key)        
    return value
