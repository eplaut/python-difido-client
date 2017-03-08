import sys
import requests

from collections import defaultdict, Counter
from backslash import Backslash as BackslashClient

base_url = 'http://difido-server:8080/api/'
machines_url = base_url + 'executions/{execution}/machines'
machine_url = machines_url + '/{machine}'
machines_data = defaultdict(list)
backslash_client = BackslashClient('http://backslash')


def create_execution(description):
    """

    :type execution_id: int
    :type machine_name: str
    :rtype: int
    """
    execution_data = {
        "description": description,
        "executionProperties": {
            "key0": "val0",
            "key1": "val2"
        },
        "shared": False,
        "forceNew": False
    }
    response = requests.post(base_url + 'executions/', json=execution_data)
    response.raise_for_status()
    return response.json()

def create_machine(execution_id, machine_name):
    """

    :type execution_id: int
    :type machine_name: str
    :rtype: int
    """
    machine_data = {
        "type": "machine",
        "name": machine_name,
        "status": "success",
        "children": None
    }
    response = requests.post(machines_url.format(execution=execution_id), json=machine_data)
    response.raise_for_status()
    return response.json()


for session in backslash_client.query_sessions().query(id=sys.argv[1:]):
    for test in session.query_tests():
        machine_name = test.test_metadata['Machine Name']
        test_data = {
            'type': test.type,
            'name': test.name,
            'status': test.status.lower(),
            'index': len(machines_data[machine_name]),
            'uid': test.logical_id,
            'duration': test.duration,
            'timestamp': test.start_time
        }
        machines_data[machine_name].append(test_data)

    execution_id = create_execution('{s.logical_id} - {s.id}'.format(s=session))
    for machine_name, machine_data in machines_data.iteritems():
        machine_id = create_machine(execution_id, machine_name)
        status_counter = Counter(test_data['status'] for test_data in machine_data)
        machine_status = 'unknown'
        for status_name in ['error', 'failure', 'success']:
            if status_name in status_counter:
                machine_status = status_name
                break
        scenario_data = {
            'type': 'scenario',
            'name': session.logical_id,
            'status': 'error',
            'children': machine_data,
            'scenarioProperties': {
                'station': session.hostname,
                'sutFile': 'unknown.xml',
                'version': session.product_version,
                'user': session.user_name,
                'testDir': 'unknown'
            }
        }
        machine_data = {
            'children': [scenario_data],
            'name': machine_name,
            'status': machine_status,
            'type': 'machine'
        }
        requests.put(machine_url.format(execution=execution_id, machine=machine_id), json=machine_data)

    requests.put(base_url + 'executions/{}?active=true'.format(execution_id))
