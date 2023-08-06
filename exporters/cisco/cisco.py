from exporters import exporter
from lib import timing
from lib import util
from datetime import datetime, timedelta
from collections import defaultdict
import sys
import json
import argparse
import subprocess
import multiprocessing
import asyncio

class InterfaceState():
    DOWN = 0
    UP = 1

class InterfacePortMode():
    ACCESS = 0
    TRUNK = 1

class BGPNeighborState():
    IDLE = 0
    CONNECT = 1
    ACTIVE = 2
    OPENSENT = 3
    OPENCONFIRM = 4
    ESTABLISHED = 5

'''
    Run command on switch and return result, this intentionally
    has no exception handling, because I'd like the program to fail
    when there is a switch communication problem, because it is a big deal
'''
async def asyncio_switch_command(switch_hostname, command, retries=2):
    for x in range(1, retries+1):
        try:
            handle = await asyncio.create_subprocess_shell(
                f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no -n admin@{switch_hostname} '{command}'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(handle.communicate(), timeout=15)

            if handle.returncode > 0:
                raise Exception(f"Status code >0. Stderr: {stderr.decode()}")
            else:
                break    
        except:
            if x == retries:
                print(f"Command failed after {retries} tries.")
                raise

    return stdout.decode()

'''
    This runs on coroutines to speed things up
'''
async def asyncio_get_metrics_from_switch(switch_hostname):
    data = {
        'switch': switch_hostname,
        'commands': {}
    }

    commands = {
        'system_resources': 'show system resources | json',
        'interfaces': 'show interface | json',
        'interface_counters': 'show interface counters detailed | json',
        'bgp_summary': 'show bgp all summary | json'
    }

    for key, command in commands.items():
        with timing.Timer() as timer:
            output = json.loads(await asyncio_switch_command(switch_hostname, command))
        
        data['commands'][key] = {
            'output': output,
            'time': timer.value
        }

    return data

class CiscoExporter(exporter.Exporter):
    job_name = 'CiscoExporter'
    
    default_switches = [
        'core-sw01', 'core-sw02', 
        'rack-sw01', 'rack-sw02', 'rack-sw03', 'rack-sw04', 'rack-sw05', 'rack-sw06'
    ]

    '''
        Get value from enum or -1
    '''
    def from_enum(self, enum, value):
        mapped = getattr(enum, value.upper(), -1)

        if mapped == -1:
            if self.debug:
                print (f"cannot map value {value} to enum {enum}")

        return mapped
    
    '''
        Takes configuration values from commandline arguments
    '''
    def parse_args(self, *args):
        parser = argparse.ArgumentParser(
            prog=self.__class__.__name__,
            description="Collects metrics from Cisco switches",
            epilog="",
            # add_help=False
        )
        exporter_arguments = parser.add_argument_group('possible exporter arguments')

        exporter_arguments.add_argument(
            '--target', metavar="TARGET", help="specify target, otherwise all", default=None
        )

        parsed_args = parser.parse_args(args)

        return parsed_args

    # preps metrics references
    @timing.observed
    def create_metrics(self):
        self.cisco_metrics_wanted = {
            'eth': {
                'eth_txload':       (self.metrics.Gauge, float),
                'eth_rxload':       (self.metrics.Gauge, float),
                'eth_bw':           (self.metrics.Gauge, float),
                'eth_mode':         (self.metrics.Gauge, self.interface_port_mode_to_value),
                'eth_state':        (self.metrics.Gauge, self.interface_state_to_value),
                'eth_admin_state':  (self.metrics.Gauge, self.interface_state_to_value)
            },
            'svi': {
                'svi_bw':               (self.metrics.Gauge, float),
                'svi_rx_load':          (self.metrics.Gauge, float),
                'svi_tx_load':          (self.metrics.Gauge, float),
                'svi_admin_state':      (self.metrics.Gauge, self.interface_state_to_value),
                'svi_state':            (self.metrics.Gauge, self.interface_state_to_value)
            },
            'bgp_saf': {
                'configuredpeers':      (self.metrics.Gauge, float),
                'capablepeers':         (self.metrics.Gauge, float),
                'totalnetworks':        (self.metrics.Gauge, float),
                'totalpaths':           (self.metrics.Gauge, float),
                'memoryused':           (self.metrics.Gauge, float),
                'numberattrs':          (self.metrics.Gauge, float),
                'bytesattrs':           (self.metrics.Gauge, float),
                'numberpaths':          (self.metrics.Gauge, float),
                'bytespaths':           (self.metrics.Gauge, float),
                'numbercommunities':    (self.metrics.Gauge, float),
                'bytescommunities':     (self.metrics.Gauge, float),
                'numberclusterlist':    (self.metrics.Gauge, float),
                'bytesclusterlist':     (self.metrics.Gauge, float)
            },
            'bgp_saf_neighbor': {
                'state':                 (self.metrics.Gauge, self.bgp_neighbor_state_to_value),
                'neighbortableversion':  (self.metrics.Gauge, float),
                'prefixreceived':        (self.metrics.Gauge, float),
                'msgrecvd':              (self.metrics.Counter, float),
                'msgsent':               (self.metrics.Counter, float),
                'inq':                   (self.metrics.Counter, float),
                'outq':                  (self.metrics.Counter, float)
            },
            'interface_counters_eth': {
                'eth_inbytes':      (self.metrics.Counter, float),
                'eth_indiscard':    (self.metrics.Counter, float),
                'eth_inerr':        (self.metrics.Counter, float),
                'eth_inpkts':       (self.metrics.Counter, float),
                'eth_ingiants':     (self.metrics.Counter, float),
                'eth_outbytes':     (self.metrics.Counter, float),
                'eth_outdiscard':   (self.metrics.Counter, float),
                'eth_outerr':       (self.metrics.Counter, float),
                'eth_outpkts':      (self.metrics.Counter, float),
                'eth_outgiants':    (self.metrics.Counter, float)
            },
            'interface_counters_svi': {
                'svi_total_pkts_out':  (self.metrics.Counter, float),
                'svi_total_bytes_out': (self.metrics.Counter, float),
                'svi_total_pkts_in':   (self.metrics.Counter, float),
                'svi_total_bytes_in':  (self.metrics.Counter, float),
                'svi_ucast_bytes_out': (self.metrics.Counter, float),
                'svi_ucast_pkts_out':  (self.metrics.Counter, float),
                'svi_ucast_bytes_in':  (self.metrics.Counter, float),
                'svi_ucast_pkts_in':   (self.metrics.Counter, float)
            },
            'system_resources': {
                'memory_usage_total': (self.metrics.Gauge, float),
                'memory_usage_used':  (self.metrics.Gauge, float),
                'memory_usage_free':  (self.metrics.Gauge, float),
                'processes_total':    (self.metrics.Gauge, float),
                'processes_running':  (self.metrics.Gauge, float),
                'cpu_state_user':     (self.metrics.Gauge, float),
                'cpu_state_kernel':   (self.metrics.Gauge, float),
                'cpu_state_idle':     (self.metrics.Gauge, float)
            }
        }

        cisco_metric_config = {
            'eth': {
                'labels': ['instance', 'interface', 'hwaddr', 'description'],
                'helptext': 'From show interfaces',
                'prefix_with_category_name': False
            },
            'svi': {
                'labels': ['instance', 'interface', 'hwaddr'],
                'helptext': 'From show interfaces',
                'prefix_with_category_name': False
            },
            'bgp_saf': {
                'labels': ['instance', 'af_id', 'router_id', 'local_as'],
                'helptext': 'From show bgp summary all',
                'prefix_with_category_name': True
            },
            'bgp_saf_neighbor': {
                'labels': ['instance', 'af_id', 'neighborid', 'router_id', 'local_as', 'neighboras'],
                'helptext': 'From show bgp summary all',
                'prefix_with_category_name': True
            },
            'interface_counters_eth': {
                'labels': ['instance', 'interface', 'description'],
                'helptext': 'From show interface counters detailed',
                'prefix_with_category_name': False
            },
            'interface_counters_svi': {
                'labels': ['instance', 'interface'],
                'helptext': 'From show interface counters detailed',
                'prefix_with_category_name': False
            },
            'system_resources': {
                'labels': ['instance'],
                'helptext': 'From show system resources',
                'prefix_with_category_name': False
            }
        }

        self.metric_refs = {}

        for category, metrics in self.cisco_metrics_wanted.items():
            for metric_source, data in metrics.items():
                handler, formatter = data

                prefix = f"cisco"
                if cisco_metric_config[category]['prefix_with_category_name']:
                    prefix = f"{prefix}_{category}"

                metric_name = f"{prefix}_{metric_source}"
                
                self.metric_refs[metric_name] = {
                    'metric': handler(metric_name, cisco_metric_config[category]['helptext'], cisco_metric_config[category]['labels']),
                    'formatter': formatter
                }

                if handler == self.metrics.Counter:
                    self.metric_refs[metric_name]['setter'] = 'inc'
                else:
                    self.metric_refs[metric_name]['setter'] = 'set'

    def bgp_neighbor_state_to_value(self, state):
        return self.from_enum(BGPNeighborState, state)
    
    def interface_state_to_value(self, state):
        return self.from_enum(InterfaceState, state)

    def interface_port_mode_to_value(self, mode):
        return self.from_enum(InterfacePortMode, state)

    def is_interface_svi(self, blob):
        if blob['interface'].startswith('Vlan'):
            return True

        for k in ['svi_admin_state', 'svi_total_pkts_in', 'svi_ucast_bytes_in']:
            if k in blob.keys():
                return True
        
        return False

    # set value using metric formatter and setter
    # return the set value
    def add_metric_value(self, metric_name, labels, value):
        ref = self.metric_refs[metric_name]['metric'].labels(*labels)
        formatter = self.metric_refs[metric_name]['formatter']
        
        new_value = formatter(value)

        getattr(ref, self.metric_refs[metric_name]['setter'])(new_value)

        return new_value

    # svi interface
    @timing.observed
    def add_svi_metrics(self, switch_hostname, interface_data):
        interface = interface_data['interface']
        hwaddr = interface_data['svi_mac']

        current_state = self.add_metric_value('cisco_svi_state', [switch_hostname, interface, hwaddr], interface_data['svi_line_proto'])

        try:
            self.add_metric_value('cisco_svi_admin_state', [switch_hostname, interface, hwaddr], interface_data['svi_admin_state'])
        except:
            pass

        if current_state < 1:
            return

        for metric_source, metric_type in self.cisco_metrics_wanted['svi'].items():
            metric_name = f"cisco_{metric_source}"

            try:
                self.add_metric_value(metric_name, [switch_hostname, interface, hwaddr], interface_data[metric_source])
            except:
                pass

    # eth interface
    @timing.observed
    def add_eth_metrics(self, switch_hostname, interface_data):
        interface = interface_data['interface']
        hwaddr = interface_data['eth_hw_addr']
        description = self.interface_descriptions[switch_hostname][interface]

        current_state = self.add_metric_value('cisco_eth_state', [switch_hostname, interface, hwaddr, description], interface_data['state'])

        try:
            self.add_metric_value('cisco_eth_admin_state', [switch_hostname, interface, hwaddr, description], interface_data['admin_state'])
        except:
            pass

        if current_state < 1:
            return

        for metric_source, metric_type in self.cisco_metrics_wanted['eth'].items():
            metric_name = f"cisco_{metric_source}"

            try:
                self.add_metric_value(metric_name, [switch_hostname, interface, hwaddr, description], interface_data[metric_source])
            except:
                pass

    # fill out interface description
    def add_eth_description(self, switch_hostname, data):
        if switch_hostname not in self.interface_descriptions.keys():
            self.interface_descriptions[switch_hostname] = {}

        interface_name = data['interface']

        interface_description = 'unknown'
        if 'desc' in data.keys():
            interface_description = data['desc']

        self.interface_descriptions[switch_hostname][interface_name] = interface_description

    # collect data from interfaces
    # also fill out descriptions of interfaces
    # to be used later
    @timing.observed
    def collect_switch_interfaces(self, switch_hostname, data):
        for row in data['TABLE_interface']['ROW_interface']:
            if self.is_interface_svi(row):
                self.add_svi_metrics(switch_hostname, row)
                continue

            self.add_eth_description(switch_hostname, row)
            self.add_eth_metrics(switch_hostname, row)

    # collect data from interface counters
    @timing.observed
    def collect_switch_interface_counters(self, switch_hostname, data):
        for interface_row in data['TABLE_interface']['ROW_interface']:
            interface = interface_row['interface']

            if self.is_interface_svi(interface_row):
                category = 'interface_counters_svi'
                labels = [switch_hostname, interface]
            else:
                category = 'interface_counters_eth'
                description = self.interface_descriptions[switch_hostname][interface]
                labels = [switch_hostname, interface, description]

            for metric_source, metric_type in self.cisco_metrics_wanted[category].items():
                metric_name = f"cisco_{metric_source}"

                try:
                    self.add_metric_value(metric_name, labels, interface_row[metric_source])
                except:
                    pass

    # bgp data - neightbors states
    @timing.observed
    def collect_switch_bgp_summary(self, switch_hostname, data):
        data = data['TABLE_vrf']['ROW_vrf']

        if type(data) is not list:
            data = [data]

        for row_vrf in data:
            router_id = row_vrf['vrf-router-id']
            local_as = row_vrf['vrf-local-as']

            if type(row_vrf['TABLE_af']['ROW_af']) is not list:
                row_vrf['TABLE_af']['ROW_af'] = [row_vrf['TABLE_af']['ROW_af']]

            for row_af in row_vrf['TABLE_af']['ROW_af']:
                af_id = row_af['af-id']

                for metric_source in self.cisco_metrics_wanted['bgp_saf'].keys():
                    metric_name = f"cisco_bgp_saf_{metric_source}"

                    try:
                        self.add_metric_value(metric_name, [switch_hostname, af_id, router_id, local_as], row_af['TABLE_saf']['ROW_saf'][metric_source])
                    except:
                        pass

                try:
                    for neighbor in row_af['TABLE_saf']['ROW_saf']['TABLE_neighbor']['ROW_neighbor']:
                        neighborid = neighbor['neighborid']
                        neighboras = neighbor['neighboras']

                        for metric_source in self.cisco_metrics_wanted['bgp_saf_neighbor'].keys():
                            metric_name = f"cisco_bgp_saf_neighbor_{metric_source}"

                            self.add_metric_value(metric_name, [switch_hostname, af_id, neighborid, router_id, local_as, neighboras], neighbor[metric_source])
                except:
                    pass

    # system resources
    @timing.observed
    def collect_switch_system_resources(self, switch_hostname, data):
        labels = [switch_hostname]

        for metric_source, metric_type in self.cisco_metrics_wanted['system_resources'].items():
            metric_name = f"cisco_{metric_source}"

            try:
                self.add_metric_value(metric_name, labels, data[metric_source])
            except:
                pass

    async def gather_async(self, switches):
        tasks = [asyncio_get_metrics_from_switch(switch) for switch in switches]
        raw_data = await asyncio.gather(*tasks, return_exceptions=True)

        return raw_data

    def gather_metrics(self):
        if self.args.target is None:
            switches = self.default_switches
        else:
            switches = [ self.args.target ]

        self.create_metrics()
        self.interface_descriptions = {}

        # with timing.Observe(self, 'get_metrics_from_switch'):
        raw_data = asyncio.run(self.gather_async(switches))

        timer_metric = self.metrics.Gauge("cisco_command_runtime", "Time taken to obtain data from switch", ['instance', 'command'])
        
        for item in raw_data:
            for command, command_data in item['commands'].items():
                timer_metric.labels(item['switch'], command).set(command_data['time'])

            self.collect_switch_system_resources(item['switch'], item['commands']['system_resources']['output'])
            self.collect_switch_bgp_summary(item['switch'], item['commands']['bgp_summary']['output'])
            self.collect_switch_interfaces(item['switch'], item['commands']['interfaces']['output'])
            self.collect_switch_interface_counters(item['switch'], item['commands']['interface_counters']['output'])
