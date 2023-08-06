# Cisco Exporter

Scrapes Cisco switches for metrics

Must be able to connect as admin@ to switches

## Usage

```
usage: CiscoExporter [-h] [--target TARGET]

Collects metrics from Cisco switches

optional arguments:
  -h, --help       show this help message and exit

possible exporter arguments:
  --target TARGET  specify target, otherwise all
```

## common labels:

All metrics have below labels:

Labels:

| label       | description                                                     | example value  |
| ----------- | --------------------------------------------------------------- | -------------- |
| instance    | switch hostname                                                 | rack-sw01      |

## metrics: system resources

Following metrics are extracted from `show system resources | json`:

| metric             | description                           | type  | example value |
| ------------------ | ------------------------------------- | ----- | ------------- |
| memory_usage_total | Total memory, KiB                     | gauge | 55345345      |
| memory_usage_used  | Used memory, KiB                      | gauge | 55433         |
| memory_usage_free  | Free memory, KiB                      | gauge | 534533        |
| processes_total    | Number of processes in the system     | gauge | 7             |
| processes_running  | Number of processes currently running | gauge | 1             |
| cpu_state_user     | CPU state: user, percent              | gauge | 50            |
| cpu_state_kernel   | CPU state: kernel, percent            | gauge | 52            |
| cpu_state_idle     | CPU state: idle, percent              | gauge | 51            |

## metrics: interfaces

Labels:

| label       | description                                                     | example value  |
| ----------- | --------------------------------------------------------------- | -------------- |
| interface   | name of interface                                               | Ethernet1/41   |
| description | port description, or unknown if none (ethernet interfaces only) | czj30600hf,1   |
| hwaddr      | interface mac address                                           | aabb.ccdd.eeff |

Following metrics are extracted from `show interfaces | json`:

| metric                | description                                                 | type  | example value |
| --------------------- | ----------------------------------------------------------- | ----- | ------------- |
| cisco_eth_txload      | Ethernet TX Load                                            | gauge | 1             |
| cisco_eth_rxload      | Ethernet RX Load                                            | gauge | 1             |
| cisco_eth_bw          | Ethernet link speed                                         | gauge | 10000         |
| cisco_eth_mode        | Ethernet link mode: `0` is access, `1` is trunk             | gauge | 1             |
| cisco_eth_state       | Ethernet current link state: `-1` unknown, `0` down, `1` up | gauge | 1             |
| cisco_eth_admin_state | Ethernet link admin state, same values as eth_state         | gauge | 1             |
| cisco_svi_txload      | SVI TX Load                                                 | gauge | 1             |
| cisco_svi_rxload      | SVI RX Load                                                 | gauge | 1             |
| cisco_svi_bw          | SVI link speed                                              | gauge | 10000         |
| cisco_svi_state       | SVI current link state: `-1` unknown, `0` down, `1` up      | gauge | 1             |
| cisco_svi_admin_state | SVI link admin state, same values as svi_state              | gauge | 1             |

## metrics: interface counters

Labels:

| label       | description                                                     | example value  |
| ----------- | --------------------------------------------------------------- | -------------- |
| interface   | name of interface                                               | Ethernet1/41   |
| description | port description, or unknown if none (ethernet interfaces only) | czj30600hf,1   |

Following metrics are extracted from `show interface counters detailed | json`:

| metric                                                          | description                        | type    | example value |
| --------------------------------------------------------------- | ---------------------------------- | ------- | ------------- |
| cisco_eth_inbytes_total, cisco_eth_outbytes_total               | Ethernet: bytes in/out             | counter | 15345345      |
| cisco_eth_indiscard_total, cisco_eth_outdiscard_total           | Ethernet: discarded packets in/out | counter | 15345345      |
| cisco_eth_inerr_total, cisco_eth_outerr_total                   | Ethernet: error packets in/out     | counter | 15345345      |
| cisco_eth_inpkts_total, cisco_eth_outpkts_total                 | Ethernet: packets in/out           | counter | 15345345      |
| cisco_eth_ingiants_total, cisco_eth_outgiants_total             | Ethernet: giant packets in/out     | counter | 15345345      |
| cisco_svi_total_pkts_in_total, cisco_svi_total_pkts_out_total   | SVI: packets in/out                | counter | 15345345      |
| cisco_svi_total_bytes_in_total, cisco_svi_total_bytes_out_total | SVI: bytes in/out                  | counter | 15345345      |
| cisco_svi_ucast_pkts_in_total, cisco_svi_ucast_pkts_out_total   | SVI: unicast packets in/out        | counter | 15345345      |
| cisco_svi_ucast_bytes_in_total, cisco_svi_ucast_bytes_out_total | SVI: unicast bytes in/out          | counter | 15345345      |

## metrics: bgp summary

Labels:

| label                                | description          | example value   |
| ------------------------------------ | -------------------- | --------------- |
| af_id                                | autonomous fabric ID | Ethernet1/41    |
| local_as                             | local ASN            | 60000           |
| router_id                            | router ID            | 192.168.100.254 |
| neighborid (cisco_bgp_saf_neighbor*) | peer ID              | 192.168.100.200 |
| neighboras (cisco_bgp_saf_neighbor*) | peer ASN             | 65000           |

Following metrics are extracted from `show bgp all summary | json`:

| metric                                      | description                                                                                                     | type    | example value |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ------- | ------------- |
| cisco_bgp_saf_configuredpeers               | Number of currently configured peers                                                                            | gauge   | 16            |
| cisco_bgp_saf_capablepeers                  | Capable/online peers                                                                                            | gauge   | 16            |
| cisco_bgp_saf_totalnetworks                 | Number of BGP networks                                                                                          | gauge   | 5             |
| cisco_bgp_saf_totalpaths                    | Number of known paths                                                                                           | gauge   | 16            |
| cisco_bgp_saf_memoryused                    | BGP table memory usage (bytes?)                                                                                 | gauge   | 1000          |
| cisco_bgp_saf_numberattrs                   | todo: explain                                                                                                   | gauge   | 10            |
| cisco_bgp_saf_bytesattrs                    | todo: explain                                                                                                   | gauge   | 1000          |
| cisco_bgp_saf_numberpaths                   | todo: explain                                                                                                   | gauge   | 1000          |
| cisco_bgp_saf_bytespaths                    | todo: explain                                                                                                   | gauge   | 1000          |
| cisco_bgp_saf_numbercommunities             | todo: explain                                                                                                   | gauge   | 1000          |
| cisco_bgp_saf_bytescommunities              | todo: explain                                                                                                   | gauge   | 1000          |
| cisco_bgp_saf_numberclusterlist             | todo: explain                                                                                                   | gauge   | 1000          |
| cisco_bgp_saf_neighbor_state                | Neighbor state: `-1` unknown, `0` idle, `1` connect, `2` active, `3` opensent, `4` openconfirm, `5` established | gauge   | 5             |
| cisco_bgp_saf_neighbor_neighbortableversion | todo: explain                                                                                                   | gauge   | 1000          |
| cisco_bgp_saf_neighbor_prefixreceived       | todo: explain                                                                                                   | gauge   | 1000          |
| cisco_bgp_saf_neighbor_msgrecvd             | todo: explain                                                                                                   | counter | 1000          |
| cisco_bgp_saf_neighbor_msgsent              | todo: explain                                                                                                   | counter | 1000          |
| cisco_bgp_saf_neighbor_inq                  | todo: explain                                                                                                   | counter | 1000          |
| cisco_bgp_saf_neighbor_outq                 | todo: explain                                                                                                   | counter | 1000          |
