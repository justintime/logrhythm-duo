#!/usr/bin/env python3
from __future__ import absolute_import
from __future__ import print_function
import six.moves.configparser
import argparse
import json
import logging
import os
import sys
import time
import duo_client
from logging.handlers import TimedRotatingFileHandler
# For proxy support
import urllib.parse


class BaseLog(object):

    def __init__(self, admin_api, log_path):
        self.admin_api = admin_api
        self.mintime   = 0
        self.events    = []

        # Set up our logger
        log_file   = os.path.join(log_path, self.__class__.__name__) + ".log"
        logger     = logging.getLogger(self.__class__.__name__)
        formatter  = logging.Formatter('%(message)s')
        loghandler = TimedRotatingFileHandler(log_file,
                                              when='midnight',
                                              interval=1,
                                              backupCount=7)
        loghandler.setLevel(logging.INFO)
        logger.setLevel(logging.INFO)
        loghandler.setFormatter(formatter)
        logger.addHandler(loghandler)

        self.logger = logger

    def get_events(self):
        try:
            self.fetch_events()
        except RuntimeError as e:
            errmsg = e.args[0]
            if errmsg == 'Received 429 Too Many Requests':
                print("Duo is throttling requests, exiting.")
                sys.exit(0)

    def fetch_events(self):
        raise NotImplementedError

    def write_logs(self):
        raise NotImplementedError

    def set_mintime(self,new_mintime):
        self.mintime = new_mintime

    def update_mintime(self):
        """
            Determine the mintime based on the timestamp of the last event
        """
        if self.events:
            self.mintime = self.events[-1]['timestamp'] + 1

        return self.mintime

class AdministratorLog(BaseLog):
    def __init__(self, admin_api, log_path):
        BaseLog.__init__(self, admin_api, log_path)


    def fetch_events(self):
        self.events = self.admin_api.get_administrator_log(
            mintime=self.mintime,
        )

    def write_logs(self):
        """
        Return an list of log messages
        """
        # To get a list of current actions without a friendly label, run:
        # cat AdministratorLog.log* | cut -d',' -f5 | cut -d'"' -f2 | sort -u | grep _
        friendly_label = {
            'ad_sync_begin' : "Active Directory Sync Start",
            'ad_sync_finish' : "Active Directory Sync Finish",
            'admin_2fa_error': "Admin 2FA Error",
            'admin_create': "Create Admin",
            'admin_delete': "Delete Admin",
            'admin_login': "Admin Login",
            'admin_login_error': "Admin Login Error",
            'admin_reset_password': "Admin Password Reset",
            'admin_send_reset_password_email': "Admin Send Password Reset Email",
            'admin_update': "Update Admin",
            'customer_update': "Update Customer",
            'group_create': "Create Group",
            'group_udpate': "Update Group",
            'group_delete': "Delete Group",
            'integration_create': "Create Integration",
            'integration_update': "Update Integration",
            'integration_delete': "Delete Integration",
            'integration_skey_view': "Admin Viewed Integration Secret Key",
            'phone_create': "Create Phone",
            'phone_update': "Update Phone",
            'phone_delete': "Delete Phone",
            'user_create': "Create User",
            'user_update': "Update User",
            'user_delete': "Delete User"
        }
        fmtstr_template = '%(timestamp)s,' \
            'host="%(host)s",' \
            'eventtype="%(eventtype)s",' \
            'username="%(username)s",' \
            'action="%(actionlabel)s"'

        for event in self.events:
            fmtstr = fmtstr_template
            event['actionlabel'] = friendly_label.get(
                event['action'], event['action'])


            if event['object']:
                fmtstr += ',object="%(object)s"'
            if event['description']:
                fmtstr += ',description="%(description)s"'

            self.logger.info(fmtstr % event)



class AuthenticationLog(BaseLog):
    def __init__(self, admin_api, log_path):
        BaseLog.__init__(self, admin_api, log_path)

    def fetch_events(self):
        self.events = self.admin_api.get_authentication_log(
            mintime=self.mintime,
        )

    def write_logs(self):
        """
        Return an list of log messages
        """
        fmtstr = (
                '%(timestamp)s,'
                'host="%(host)s",'
                'eventtype="%(eventtype)s",'
                'username="%(username)s",'
                'factor="%(factor)s",'
                'result="%(result)s",'
                'reason="%(reason)s",'
                'ip="%(ip)s",'
                'integration="%(integration)s",'
                'newenrollment="%(new_enrollment)s"'
            )
        for event in self.events:
            self.logger.info(fmtstr % event)



class TelephonyLog(BaseLog):
    def __init__(self, admin_api, log_path):
        BaseLog.__init__(self, admin_api, log_path)


    def fetch_events(self):
        self.events = self.admin_api.get_telephony_log(
            mintime=self.mintime,
        )

    def write_logs(self):
        """
        Return an list of log messages
        """
        fmtstr = '%(timestamp)s,' \
                 'host="%(host)s",' \
                 'eventtype="%(eventtype)s",' \
                 'context="%(context)s",' \
                 'type="%(type)s",' \
                 'phone="%(phone)s",' \
                 'credits="%(credits)s"'
        for event in self.events:
            event['host'] = self.admin_api.host
            self.logger.info(fmtstr % event)

def admin_api_from_config(config_path):
    """
    Return a duo_client.Admin object created using the parameters
    stored in a config file.
    """
    config = six.moves.configparser.ConfigParser()
    config.read(config_path)
    config_d = dict(config.items('duo'))
    ca_certs = config_d.get("ca_certs", None)
    if ca_certs is None:
        ca_certs = config_d.get("ca", None)

    ret = duo_client.Admin(
        ikey=config_d['ikey'],
        skey=config_d['skey'],
        host=config_d['host'],
        ca_certs=ca_certs,
    )

    http_proxy = config_d.get("http_proxy", None)
    if http_proxy is not None:
        proxy_parsed = urlparse(http_proxy)
        proxy_host = proxy_parsed.hostname
        proxy_port = proxy_parsed.port
        ret.set_proxy(host = proxy_host, port = proxy_port)

    return ret

def parse_args():
    parser = argparse.ArgumentParser(description='Download Duo logs to the local filesystem for LogRhythm consumption.')

    parser.add_argument("-c", "--config-file", help="Path to duo.conf, defaults to duo.conf in same directory as this script.",
                        default=os.path.join(sys.path[0], 'duo.conf'))
    parser.add_argument("-l", "--log-path", help="Path to store the log file in, defaults to the 'logs' directory beneath this script.",
                        default=os.path.join(sys.path[0], 'logs'))
    parser.add_argument("-s", "--state-path", help="Path to store the state file in, defaults to the same directory as the log file.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose mode.")
    return parser.parse_args()

def load_state_from_file(statefile):
    try:
        with open(statefile, 'r') as json_file:
            state = json.load(json_file)
    except IOError:
        state = {}
    return state

def write_state_to_file(statefile,state):
    try:
        with open(statefile, 'w') as outfile:
            json.dump(state, outfile)
    except IOError:
        print("Unable to write to " + statefile + ", exiting.")
        sys.exit(1)

def main():
    # Parse the commandline args, load our config, and set our paths
    args        = parse_args()
    config_path = args.config_file
    log_path    = args.log_path
    state_path  = args.state_path if args.state_path else args.log_path
    state_file  = os.path.join(state_path,'.state.json')
    if not os.path.exists(log_path):
        os.makedirs(log_path)

    # Load our last timestamps to prevent dupes
    state = load_state_from_file(state_file)

    # This is our object we interact with to query Duo's Admin API
    admin_api   = admin_api_from_config(config_path)

    for logclass in (AdministratorLog, AuthenticationLog, TelephonyLog):
        log = logclass(admin_api,log_path)

        # Load our previous state, creating the default if it doesn't exist
        state_index = log.__class__.__name__
        try:
            mintime = state[state_index]['last_timestamp'] or 0
        except KeyError:
            mintime = 0
            state[state_index] = {'last_timestamp': 0}

        log.set_mintime(mintime)
        # Fetch the events
        log.get_events()
        if args.verbose: print("Recieved " + str(len(log.events)) + " logs from the " + log.__class__.__name__)
        # Format the events and write them to the logs
        log.write_logs()
        # Update our last recorded timestamp
        state[state_index]['last_timestamp'] = log.update_mintime()

        # Save our state to a json file
        write_state_to_file(state_file, state)

if __name__ == '__main__':
    main()
