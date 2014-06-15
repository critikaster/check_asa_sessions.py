#!/usr/bin/env python3

'''
Icinga (Nagios) plugin that checks the total amount of current, concurrent
sessions on a Cisco ASA and evaluates them against 'warning' and 'critical' value
thresholds.
'''

__version__ = 'v0.2'
__author__ = 'raoul@node00.nl'

import sys
import argparse
import subprocess


def ok(msg):
    print('OK:', msg)
    sys.exit(0)


def warning(msg):
    print('WARNING:', msg)
    sys.exit(1)


def critical(msg):
    print('CRITICAL:', msg)
    sys.exit(2)


def unknown(msg):
    print('UNKNOWN:', msg)
    sys.exit(3)


def error(msg):
    print('ERROR:', msg)
    sys.exit(3)


def check_asa_sessions(snmp_check_values):

    try:

        # Build snmpwalk command: get sessions
        command_output_sessions = subprocess.check_output(
            [
                'snmpwalk', '-v', '2c', '-c',
                snmp_check_values['snmp_community'],
                snmp_check_values['snmp_host'],
                snmp_check_values['snmp_oid_asa_sessions']
            ]
        )

        # Build snmpwalk command: get model/type
        command_output_model = subprocess.check_output(
            [
                'snmpwalk', '-v', '2c', '-c',
                snmp_check_values['snmp_community'],
                snmp_check_values['snmp_host'],
                snmp_check_values['snmp_oid_asa_model']
            ]
        )

    except:

        msg = 'Something went wrong with subprocess command \'snmpwalk\''
        msg += '\nIs the host ' + snmp_check_values['snmp_host'] + ' reachable?'
        msg += '\nIs it configured to accept SNMP polls from this host?'
        msg += '\nIs SNMP community string \'' + snmp_check_values['snmp_community'] + '\' valid?'

        error(msg)


    try:
        # Parse command output: current concurrent sessions
        current_asa_sessions = command_output_sessions.decode().split()[3]

        # Parse command output: ASA model/type
        asa_model = command_output_model.decode().split()[3].split('"')[1]

    except:
        msg = 'Something went wrong parsing data. Probably wrong SNMP OID for this device.'
        error(msg)


    # Use model/type to determine 'critical high' threshold automatically ..
    # .. But only if no 'critical high' threshold was set manually
    if snmp_check_values['high_threshold_set'] == False:
        if snmp_check_values[asa_model]:
            snmp_check_values['critical_high'] = snmp_check_values[asa_model]
        else:
            snmp_check_values['critical_high'] = snmp_check_values['UNKNOWN_MODEL']

    # DEBUG OUTPUT
    if snmp_check_values['debug'] == True:

        print('\n // DEBUG: settings //\n')

        for key, value in sorted(snmp_check_values.items()):
            print('  {key:22} :  {value:<}'.format(**locals()))
        print()

        print('\n // DEBUG: command output //\n')
        print(' Raw data:\n ', command_output_sessions)
        print(' Parsed to:\n ', current_asa_sessions)
        print('\n Raw data:\n ', command_output_model)
        print(' Parsed to:\n ', asa_model)
        print()

    # Default output message and .. | .. perfdata
    msg = 'Current sessions: ' + current_asa_sessions + ' MODEL: ' + asa_model + ' | current_sessions=' + current_asa_sessions

    # Evaluate thresholds and generate plugin status message for Icinga
    if int(current_asa_sessions) <= snmp_check_values['critical_low']:
        critical(msg)
    if snmp_check_values['critical_low'] < int(current_asa_sessions) <= snmp_check_values['warning_low']:
        warning(msg)
    if snmp_check_values['warning_low'] < int(current_asa_sessions) < snmp_check_values['warning_high']:
        ok(msg)
    if snmp_check_values['warning_high'] <= int(current_asa_sessions) < snmp_check_values['critical_high']:
        warning(msg)
    if int(current_asa_sessions) >= snmp_check_values['critical_high']:
        critical(msg)


def main():

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Icinga (Nagios) plugin that checks the total amount of current, concurrent \
        sessions on a Cisco ASA and evaluates them against \'warning\' and \'critical\' value \
        thresholds.',
        epilog='Written in Python 3.'
    )
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--debug', action='store_true', help='debug output')
    parser.add_argument('SNMP_COMMUNITY', type=str, help='the SNMP community string of the remote device')
    parser.add_argument('HOST', type=str, help='the IP of the remote host you want to check')
    parser.add_argument('-w', '--warning', type=int, help='set high warning threshold')
    parser.add_argument('-c', '--critical', type=int, help='set high critical threshold')
    parser.add_argument('-wl', type=int, help='set low warning threshold')
    parser.add_argument('-cl', type=int, help='set low critical threshold')
    args = parser.parse_args()

    # Required values
    snmp_check_values = {
        'snmp_community'            : args.SNMP_COMMUNITY,
        'snmp_host'                 : args.HOST,
        'snmp_oid_asa_model'        : '.1.3.6.1.2.1.47.1.1.1.1.13.1',
        'snmp_oid_asa_sessions'     : '.1.3.6.1.4.1.9.9.147.1.2.2.2.1.5.40.6',
        'warning_low'               : -1,   # Default: don't whine about low values
        'warning_high'              : 50000,
        'critical_low'              : -2,   # Default: don't whine about low values
        'critical_high'             : 100000,
        'high_threshold_set'        : False,
        'debug'                     : False,
        'ASA5505'                   : 10000,
        'ASA5510'                   : 50000,
        'ASA5512'                   : 280000,
        'ASA5520'                   : 280000,
        'ASA5540'                   : 400000,
        'ASA5550'                   : 650000,
        'UNKNOWN_MODEL'             : 800000
    }

    # Any thresholds set?
    if args.wl:
        snmp_check_values['warning_low'] = args.wl
    if args.cl:
        snmp_check_values['critical_low'] = args.cl
    if args.warning:
        snmp_check_values['warning_high'] = args.warning
    if args.critical:
        snmp_check_values['critical_high'] = args.critical
        # If 'critical high' is manually set now, don't use default thresholds later
        snmp_check_values['high_threshold_set'] = True

    # Debug mode enabled?
    if args.debug:
        snmp_check_values['debug'] = True

    # Do it. Do it nau.
    check_asa_sessions(snmp_check_values)


if __name__ == '__main__':
    main()



# Copyright (c) 2014, raoul@node00.nl
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.