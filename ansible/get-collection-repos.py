#!/usr/bin/python3 -tt
#
# Copyright: 2021 Ansible Project
# License: GPLv3+

"""
Retrieve the repositories that are listed on galaxy for the collections in the last ansible
package release.

* This is what the collection owner provided on galaxy.  If they didn't
  add a correct repository name (or, in some cases, added a subdirectory
  rather than the url to clone), then additional normalization of the data
  will be necessary.
* This will look for the list of collections for the latest ansible.  In
  some cases, this will be a different list than what was in the last
  release on pypi.
"""
import asyncio
import glob
import os
import pathlib
import tempfile

import aiohttp
import asyncio_pool
import sh

from antsibull.galaxy import GalaxyClient
from antsibull import compat


ANSIBLE_BUILD_DATA = 'git://github.com/ansible-community/ansible-build-data'
# Concurrent requests to the galaxy server
MAX_THREADS = 5


def get_ansible_in(url=ANSIBLE_BUILD_DATA):
    """Determine the latest ansible.in file in a path and return the path to it."""
    with tempfile.TemporaryDirectory() as tmp:
        # Checkout the ansible-build-data repo
        tmp = pathlib.Path(tmp)
        ansible_build_data_dir = tmp / 'ansible-build-data'
        sh.git('clone', ANSIBLE_BUILD_DATA, ansible_build_data_dir)

        # Determine which directory has the latest ansible.in file
        version_dirs = [f for f in glob.glob(str(ansible_build_data_dir / '[0-9]*'))
                        if os.path.isdir(f)]
        version_dirs.sort(reverse=True)

        for directory in version_dirs:
            ansible_in = os.path.join(directory, 'ansible.in')
            if os.path.exists(ansible_in):
                break
        else:  # Python for-else
            raise Exception('No directory in ansible-build-data was found with an ansible.in file')

        # Retrieve the data.  This file should always be reasonably small
        with open(ansible_in, 'rb') as f:
            ansible_in_data = f.read()
            ansible_in_data = ansible_in_data.decode('utf-8')

    return ansible_in_data


def get_collections(ansible_in_data):
    """Return a list of collections from the ansible.in contents."""
    # Remove blank lines and comment lines; split the string into a list
    collections = [line.strip() for line in ansible_in_data.split('\n')
                   if line.strip() and not line.strip().startswith('#')]
    return collections


async def retrieve_one_git_repo_url(client, collection):
    """Retrieve the git repo url for one collection."""
    collection_info = await client.get_info(collection)
    latest = collection_info['latest_version']['version']

    collection_release_info = await client.get_release_info(collection, latest)

    return collection_release_info['metadata'].get('repository', 'No git repository listed')


async def retrieve_all_git_repo_urls(collection_list):
    """Retrieve the git repo urls for all collections in a list."""
    requestors = {}
    async with aiohttp.client.ClientSession() as session:
        async with asyncio_pool.AioPool(size=MAX_THREADS) as pool:
            client = GalaxyClient(session)
            for collection in collection_list:
                requestors[collection] = await pool.spawn(
                    retrieve_one_git_repo_url(client, collection))

            responses = await asyncio.gather(*requestors.values())

    # Note: Python dicsts have a stable sort order and since we haven't modified the dict since
    # we used requestors.values(), the order of requestors and responses will still match.
    collection_repos = dict(zip(requestors, responses))
    return collection_repos

def main():
    # Retrieve the collections in the latest, in progress ansible package.
    latest_ansible_in_data = get_ansible_in()

    # Get the list of collections from there
    collection_list = get_collections(latest_ansible_in_data)

    # Retrieve the github repo for each collection on galaxy.
    collection_repos = compat.asyncio_run(retrieve_all_git_repo_urls(collection_list))

    for collection, repo in sorted(collection_repos.items()):
        print(f'{collection}: {repo}')

    return 0
    

if __name__ == '__main__':
    main()
