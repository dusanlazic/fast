import re
import ipaddress
from itertools import product


IPV4_PATTERN = r'(?:[0-9]{1,3}(?:-[0-9]{1,3})?(?:\.|$)){4}'


def process_targets(target_entries):
    """
    Process a list of target entries, which can include IPv4 addresses, IPv6 addresses, 
    IPv4 ranges, IPv6 ranges, and hostnames.
    """
    hosts = []

    for entry in target_entries:
        # Single IPv4 and IPv6
        try:
            ip = ipaddress.ip_address(entry)
            hosts.append(ip.exploded)
            continue
        except ValueError:
            pass
        # IPv4 range
        if re.match(IPV4_PATTERN, entry):
            hosts.extend(expand_ipv4_range(entry))
            continue
        # IPv6 range
        if ':' in entry:
            hosts.extend(expand_ipv6_range(entry))
            continue
        # Hostname
        hosts.append(entry)
    
    return hosts


def expand_ipv4_range(ip_range):
    """
    Expand an IPv4 range into a list of individual IPv4 addresses.
    """
    octets = ip_range.split('.')
    ranges = [list(range(int(octet.split('-')[0]), int(octet.split('-')[1]) + 1))
              if '-' in octet else [int(octet)] for octet in octets]
    return ['.'.join(map(str, octets)) for octets in product(*ranges)]


def expand_ipv6_range(ip_range):
    """
    Expand an IPv6 range into a list of individual IPv4 addresses.
    """
    ip_range = explode_ipv6_range(ip_range)
    hextets = ip_range.split(':')
    ranges = [list(range(int(hextet.split('-')[0], 16), int(hextet.split('-')[1], 16) + 1))
              if '-' in hextet else [int(hextet, 16)] for hextet in hextets]
    return [compress(explode_ipv6_range(':'.join(map(lambda x: format(x, 'x'), hextets)))) for hextets in product(*ranges)]


def explode_ipv6_range(ip):
    """
    Convert a shorthand IPv6 address range into its full "exploded" form for easier range processing.
    """
    hextets = ip.split(":")
    missing_hextets = 8 - len([h for h in hextets if h])

    exploded_ip = ip.replace("::", ":" + ":".join("0" * missing_hextets) + ":")

    if exploded_ip.endswith(":"):
        exploded_ip = exploded_ip[:-1]
    if exploded_ip.startswith(":"):
        exploded_ip = exploded_ip[1:]

    hextets = exploded_ip.split(":")
    exploded_ip = ":".join(h.zfill(4) if '-' not in h else h for h in hextets)

    return exploded_ip


def wrap(host):
    """
    Wrap an IPv6 address in square brackets, as required by the requests module for URL formatting.
    
    This function takes a host (either a hostname or an IP address) and returns it in a format
    suitable for use in a URL. If the host is an IPv6 address, it wraps the address in square brackets.
    For IPv4 addresses and hostnames, the host is returned as-is.
    """
    try:
        ip = ipaddress.ip_address(host)
        if ip.version == 6:
            return '[' + ip.compressed + ']'
        return host
    except ValueError:
        return host


def compress(host):
    """
    Compress an IPv6 address using the standard compressed form.
    
    This function takes a host (either a hostname or an IP address) and returns it in compressed form
    if it's an IPv6 address. For IPv4 addresses and hostnames, the host is returned as-is.
    """
    try:
        ip = ipaddress.ip_address(host)
        if ip.version == 6:
            return ip.compressed
        return host
    except ValueError:
        return host


def are_hosts_equal(host1, host2):
    try:
        ip1 = ipaddress.ip_address(host1)
        ip2 = ipaddress.ip_address(host2)
        return ip1 == ip2
    except ValueError:
        return host1.strip() == host2.strip()
