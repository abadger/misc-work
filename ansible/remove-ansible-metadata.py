#!/usr/bin/python3.8 -tt

import sys

import redbaron


def main():
    module = sys.argv[1]
    with open(module, 'r') as f:
        refactorer = redbaron.RedBaron(f.read())

    toplevel_assignments = refactorer.find_all('assignment', recursive=False)

    for assignment in toplevel_assignments:
        if assignment.target.value == 'ANSIBLE_METADATA':
            break
    else:
        raise Exception('Could not find ANSIBLE_METADATA')

    for idx, node in enumerate(refactorer):
        if node is assignment:
            break
    else:
        raise Exception('Could not find ANSIBLE_METADATA a second time')

    del refactorer[idx]

    with open(module, 'w') as f:
        f.write(refactorer.dumps())

main()
