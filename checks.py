import datetime
import time
from enum import Enum
from typing import List

import jwt
import requests

__author__ = "@Wietze"
__copyright__ = "Copyright 2019"


class Annotation(Enum):
    NOTICE = 'notice'
    WARNING = 'warning'
    FAILURE = 'failure'


class Conclusion(Enum):
    SUCCESS = 'success'
    NEUTRAL = 'neutral'
    FAILURE = 'failure'


class GitHubChecks():
    TOKEN_MACHINE_MAN = 'application/vnd.github.machine-man-preview+json'
    TOKEN_ANTIOPE = 'application/vnd.github.antiope-preview+json'
    TOKEN_SHADOW_CAT = 'application/vnd.github.shadow-cat-preview+json'

    def __init__(self, name: str, app_id: str, pk_location: str, incoming_data: dict, base_api: str = 'https://api.github.com'):
        # Set constants
        self.NAME = name
        self.APP_ID = app_id
        self.BASE_API = base_api
        self.USER_AGENT = 'pychecks'
        with open(pk_location) as pk:
            self.PRIVATE_KEY = pk.read()

        # Parse incoming information
        check_suite = incoming_data.get('check_suite') or incoming_data.get('check_run', {}).get('check_suite')
        self.head_sha = check_suite.get('head_sha')
        self.owner, self.repo = incoming_data['repository']['full_name'].split('/')
        self.repo_id = incoming_data['repository']['id']
        self.branch = check_suite['head_branch']
        self.installation_id = incoming_data['installation']['id']
        self.git_url = incoming_data['repository']['git_url']

    def get_bearer_token(self, duration: int = 60) -> str:
        timestamp = int(self.now('UNIX'))
        payload = {'iat': timestamp, 'exp': timestamp + duration, 'iss': self.APP_ID}
        return jwt.encode(payload, self.PRIVATE_KEY, algorithm='RS256').decode('utf-8')

    def get_token(self) -> str:
        headers = {'Accept': self.TOKEN_MACHINE_MAN, 'User-Agent': self.USER_AGENT, 'Authorization': 'Bearer {}'.format(self.get_bearer_token())}
        data = {"repository_ids": [self.repo_id], "permissions": {"checks": "write"}}
        response = requests.post("{base_api}/app/installations/{installation_id}/access_tokens".format(base_api=self.BASE_API, installation_id=self.installation_id), headers=headers, json=data)
        result = response.json()
        if response.status_code != 201:
            raise Exception('Unexpected status code {}'.format(response.status_code), result.get('message'))
        return result['token']

    def start_check(self, token: str) -> None:
        headers = {'Accept': self.TOKEN_ANTIOPE, 'User-Agent': self.USER_AGENT, 'Authorization': 'token {}'.format(token)}
        data = {'name': self.NAME, 'head_sha': self.head_sha, 'status': 'in_progress', 'started_at': self.now()}
        result = requests.post('{base_api}/repos/{owner}/{repo}/check-runs'.format(base_api=self.BASE_API, owner=self.owner, repo=self.repo), json=data, headers=headers)
        if result.status_code != 201:
            raise Exception('Unexpected status code', result.json()['message'])
        self.run_id = result.json()['id']

    def complete_check(self, token: str, conclusion: Conclusion = Conclusion.SUCCESS, summary: str = None, details: str = None, annotations: List[dict] = None) -> None:
        headers = {'Accept': self.TOKEN_ANTIOPE, 'User-Agent': self.USER_AGENT, 'Authorization': 'token {}'.format(token)}
        data = {'name': self.NAME, 'head_sha': self.head_sha, 'status': 'completed', 'conclusion': conclusion, 'completed_at': self.now(), 'output':
                {'title': '{} Report'.format(self.NAME)}
                }
        if summary:
            data['output']['summary'] = summary
        if details:
            data['output']['text'] = details
        if annotations:
            data['output']['annotations'] = annotations

        result = requests.patch('{base_api}/repos/{owner}/{repo}/check-runs/{run_id}'.format(base_api=self.BASE_API, owner=self.owner, repo=self.repo, run_id=self.run_id), json=data, headers=headers)
        if result.status_code != 200:
            raise Exception('Unexpected status code', result.json()['message'])

    @staticmethod
    def create_annotation(path: str, level: Annotation, message: str, start: int, end: int) -> dict:
        return {'path': path, 'annotation_level': level, 'message': message, 'start_line': start, 'end_line': end}

    @staticmethod
    def now(date_type: str = 'ISO') -> str:
        if date_type == 'ISO':
            return datetime.datetime.now().isoformat() + 'Z'
        if date_type == 'UNIX':
            return time.time()
        raise Exception('Invalid date type')
