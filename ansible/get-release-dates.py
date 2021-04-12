#!/usr/bin/python3 -tt
import json
from collections import defaultdict

import requests

INTEREST = ['ansible', 'ansible-base', 'ansible-core']

KNOWN_BAD = defaultdict(tuple, {'ansible':
                                (
                                    # 1.9.0 was a flubbed release.  We removed the tarball and
                                    # then found we couldn't upload a new version so it ended
                                    # up being 1.9.0.1
                                    '1.9.0',
                                    # I'm not sure why 2.0.0 does not have a tarball but we
                                    # ended up releasing 2.0.0.0 on January 13, 2016 (2.0.0
                                    # was created on September 3, 2015)
                                    '2.0.0',
                                ),
                                }
                        )

def main():
    release_dates = {p: {} for p in INTEREST}

    for pkg in INTEREST:
        url = f'https://pypi.org/pypi/{pkg}/json'
        response = requests.get(url)
        release_info = response.json()['releases']

        for version, info in release_info.items():
            for release_artifact in info:
                if release_artifact['filename'].endswith('tar.gz'):
                    # upload_time is also a field if we want a shorter format:
                    #     2021-04-05T23:37:46
                    release_dates[pkg][version] = release_artifact['upload_time_iso_8601']
                    break
            else:
                if version in KNOWN_BAD[pkg]:
                    continue
                raise Exception(f'{pkg}-{version} does not have a tarball associated with it')

    print(json.dumps(release_dates, indent=4, sort_keys=True))


if __name__ == '__main__':
    main()
