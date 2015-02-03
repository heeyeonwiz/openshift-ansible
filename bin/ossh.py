#!/usr/bin/env python

import pdb
import argparse
import ansibleutil
import traceback
import sys
import os
import re


# use dynamic inventory
# list instances
# symlinked to ~/bin
# list instances that match pattern
# python!

# list environment stuff as well
# 3 states:
#  - an exact match; return result
#  - a partial match; return all regex results
#  - no match; None

class Ossh(object):
    def __init__(self):
        self.file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)))
        self.parse_cli_args()
        self.ansible = ansibleutil.AnsibleUtil()

        self.host_inventory = self.get_hosts()


        if self.args.debug:
            print self.args

        # get a dict of host inventory
        self.get_hosts()

        # parse host and user
        self.process_host()

        # perform the SSH
        if self.args.list:
            self.list_hosts()
        else:
            self.ssh()

    def parse_cli_args(self):
        parser = argparse.ArgumentParser(description='Openshift Online SSH Tool.')
        parser.add_argument('-r', '--random', action="store",
                          help="Choose a random host")
        parser.add_argument('-e', '--env', action="store",
                          help="Which environment to search for the host ")
        parser.add_argument('-d', '--debug', default=False,
                          action="store_true", help="debug mode")
        parser.add_argument('-v', '--verbose', default=False,
                          action="store_true", help="Verbose?")
        parser.add_argument('--list', default=False,
                          action="store_true", help="list out hosts")
        parser.add_argument('host')
        parser.add_argument('-c', '--command', action='store',
                            help='Command to run on remote host')
        parser.add_argument('-l', '--login_name', action='store',
                            help='User in which to ssh as')

        parser.add_argument('-o', '--ssh_opts', action='store',
                            help='options to pass to SSH.\n \
                                  "-o ForwardX11 yes"')

        self.args = parser.parse_args()

    def process_host(self):
        '''Determine host name and user name for SSH.
        '''
        self.env = None

        re_env = re.compile('\.(int|stg|prod|ops)')
        search = re_env.search(self.args.host)
        if self.args.env:
            self.env = self.args.env
        elif search:
            # take the first?
            self.env = search.groups()[0]

        # remove env from hostname command line arg if found
        if search:
            self.args.host = re_env.split(self.args.host)[0]

        # parse username if passed
        if '@' in self.args.host:
            self.user, self.host = self.args.host.split('@')
        else:
            self.host = self.args.host
            if self.args.login_name:
                self.user = self.args.login_name
            else:
                self.user = os.environ['USER']



    def get_hosts(self):
        '''Query our host inventory and return a dict where the format
           equals:

           dict['servername'] = dns_name
        '''
        # TODO: perform a numerical sort on these hosts
        # and display them
        self.host_inventory = self.ansible.build_host_dict()

    def select_host(self, regex=False):
        '''select host attempts to match the host specified
           on the command line with a list of hosts.

           if regex is specified then we will attempt to match
           all *{host_string}* equivalents.
        '''
# list environment stuff as well
# 3 states:
#  - an exact match; return result
#  - a partial match; return all regex results
#  - no match; None
        re_host = re.compile(self.host)

        exact = []
        results = []
        for hostname, server_info in self.host_inventory[self.env].items():
            if hostname.split(':')[0] == self.host:
                exact.append((hostname, server_info))
                break
            elif re_host.search(hostname):
                results.append((hostname, server_info))

        if exact:
            return exact
        elif results:
            return results
        else:
            print "Could not find specified host: %s in %s" % (self.host, self.env)

        # default - no results found.
        return None


    def list_hosts(self, limit=None):
        '''Function to print out the host inventory.

           Takes a single parameter to limit the number of hosts printed.
        '''

        if self.env:
            results = self.select_host(True)
            if len(results) == 1:
                hostname, server_info = results[0]
                sorted_keys = server_info.keys()
                sorted_keys.sort()
                for key in sorted_keys:
                    print '{0:<35} {1}'.format(key, server_info[key])
            else:
                for host_id, server_info in results[:limit]:
                    name = server_info['ec2_tag_Name']
                    ec2_id = server_info['ec2_id']
                    ip = server_info['ec2_ip_address']
                    print '{ec2_tag_Name:<35} {ec2_tag_environment:<8} {ec2_id:<15} {ec2_ip_address}'.format(**server_info)

                if limit:
                    print
                    print 'Showing only the first %d results...' % limit
                    print

        else:
            for env, host_ids in self.host_inventory.items():
                for host_id, server_info in host_ids.items():
                    name = server_info['ec2_tag_Name']
                    ec2_id = server_info['ec2_id']
                    ip = server_info['ec2_ip_address']
                    print '{ec2_tag_Name:<35} {ec2_tag_environment:<5} {ec2_id:<15} {ec2_ip_address}'.format(**server_info)

    def ssh(self):
        '''SSH to a specified host
        '''
        try:
            cmd = '/usr/bin/ssh'
            ssh_args = [cmd, '-l%s' % self.user]
            #ssh_args = [cmd, ]

            if self.args.verbose:
                ssh_args.append('-vvv')

            if self.args.ssh_opts:
                ssh_args.append("-o%s" % self.args.ssh_opts)

            result = self.select_host()
            if not result:
                return # early exit, no results

            if len(result) > 1:
                self.list_hosts(10)
                return # early exit, too many results

            # Assume we have one and only one.
            hostname, server_info = result[0]
            ip = server_info['ec2_ip_address']

            ssh_args.append(ip)

            #last argument
            if self.args.command:
                ssh_args.append("%s" % self.args.command)

            if self.args.debug:
                print "SSH to %s in %s as %s" % (hostname, self.env, self.user)

            print "Running: %s\n" % ' '.join(ssh_args)

            os.execve('/usr/bin/ssh', ssh_args, os.environ)
        except:
            print traceback.print_exc()
            print sys.exc_info()


def main():
    ossh = Ossh()


if __name__ == '__main__':
    main()

