from subprocess import check_output
from sys import stdout

from dns.zone import from_file
from dns.rdatatype import SOA

run = lambda cmd: stdout.write(str(check_output(cmd, shell=True), encoding='utf-8'))

def increment_zone(config):
    zone = from_file(config.bind_master, config.domain_base)
    serial = None
    for _, _, rdata in zone.iterate_rdatas(SOA):
        if serial:
            raise ValueError("Saw multiple SOA")
        serial = rdata.serial

    # :))))
    with open(config.bind_master, 'r+') as file:
        contents = file.read().replace(str(serial), str(serial + 1))
        file.seek(0)
        file.truncate(0)
        file.write(contents)

    print("Zone incremented from {} to {}".format(serial, serial + 1))

def reload_services(config):
    run("service nginx reload")
    run("pdns_control reload {}".format(config.domain_base))
    run("pdns_control notify {}".format(config.domain_base))
    print("Services reloaded")

