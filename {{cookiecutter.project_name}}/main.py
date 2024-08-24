#!/usr/bin/python3

'''
-----------------------------------------------------------------------------
Pokretanje aplikacije iz komandne linije, bez web servera i restova.
Tu bi bilo sve izvanjsko od aplikacije, što nije business logika.
Odnosno, stvari koje nisu vezane za pojedinu aplikaciju.
Koristi kod u folderu 'bus_logic'

Usage:
  ./main.py [-h]  [<config_file>]

Options:
  -h --help          Show this screen
  <config_file>      Konfiguracijski fajl. Default: bus_logic/myapp.yml
-----------------------------------------------------------------------------
'''

# start the app
if __name__ == '__main__':
    
