#!/usr/bin/python
from __future__ import absolute_import
from __future__ import print_function
import six.moves.configparser
import argparse
import json
import os
import sys
import time

import duo_client

# For proxy support
import urllib.parse


class BaseLog(object):

    def __init__(self, admin_api):
        self.admin_api = admin_api
        self.mintime   = 0
        self.events    = []

    def get_events(self):
        raise NotImplementedError

    def logs(self):
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
    def __init__(self, admin_api):
        BaseLog.__init__(self, admin_api)

    def get_events(self):
        self.events = self.admin_api.get_administrator_log(
            mintime=self.mintime,
        )

    def logs(self):
        """
        Return an list of log messages
        """
        logs = []
        friendly_label = {
            'admin_login': "Admin Login",
            'admin_create': "Create Admin",
            'admin_update': "Update Admin",
            'admin_delete': "Delete Admin",
            'customer_update': "Update Customer",
            'group_create': "Create Group",
            'group_udpate': "Update Group",
            'group_delete': "Delete Group",
            'integration_create': "Create Integration",
            'integration_update': "Update Integration",
            'integration_delete': "Delete Integration",
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

            logs.append(fmtstr % event)

        return logs


class AuthenticationLog(BaseLog):
    def __init__(self, admin_api):
        BaseLog.__init__(self, admin_api)

    def get_events(self):
        self.events = self.admin_api.get_authentication_log(
            mintime=self.mintime,
        )

    def logs(self):
        """
        Return an list of log messages
        """
        logs = []
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
            logs.append(fmtstr % event)

        return logs


class TelephonyLog(BaseLog):
    def __init__(self, admin_api):
        BaseLog.__init__(self, admin_api)

    def get_events(self):
        self.events = self.admin_api.get_telephony_log(
            mintime=self.mintime,
        )

    def logs(self):
        """
        Return an list of log messages
        """
        logs = []
        fmtstr = '%(timestamp)s,' \
                 'host="%(host)s",' \
                 'eventtype="%(eventtype)s",' \
                 'context="%(context)s",' \
                 'type="%(type)s",' \
                 'phone="%(phone)s",' \
                 'credits="%(credits)s"'
        for event in self.events:
            event['host'] = self.admin_api.host
            logs.append(fmtstr % event)

        return logs


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
    args        = parse_args()
    config_path = args.config_file
    log_path    = args.log_path
    state_path  = args.state_path if args.state_path else os.path.join(args.log_path,'.state.json')

    # Load our last timestamps to prevent dupes
    state = load_state_from_file(state_path)

    admin_api   = admin_api_from_config(config_path)

    for logclass in (AdministratorLog, AuthenticationLog, TelephonyLog):
        log = logclass(admin_api)
        state_index = log.__class__.__name__
        try:
            mintime = state[state_index]['last_timestamp'] or 0
        except KeyError:
            mintime = 0
            state[state_index] = {'last_timestamp': 0}

        log.set_mintime(mintime)
        log.get_events()
        with open(os.path.join(log_path, log.__class__.__name__) + ".log", 'w') as f:
            for line in log.logs():
                f.write("%s\n" % line)
        state[state_index]['last_timestamp'] = log.update_mintime()

    write_state_to_file(state_path, state)

if __name__ == '__main__':
    main()