import glob
import json
import subprocess

import checks


def run_test(incoming_data):
    check = checks.GitHubChecks('My QC', app_id='12345', pk_location='pk.pem', incoming_data=incoming_data, base_api='https://api.github.com')
    token = check.get_token()

    # Start Check
    check.start_check(token)

    # Clone repo
    server = check.git_url.replace('git://', 'https://x-access-token:{}@'.format(token))
    subprocess.call(['rm', '-r', check.repo])
    subprocess.call(['git', 'clone', '--single-branch', '--branch', check.branch, server])

    # Run tests
    an = []
    files = [(filename, open(filename)) for filename in glob.glob(check.repo + '/**/*.json', recursive=True)]
    for file_path, contents in files:
        try:
            json.loads(contents)
        except Exception as e:
            an.append(
                checks.GitHubChecks.create_annotation(file_path.replace('./'+check.repo, ''), level=checks.Annotation.FAILURE,
                                                      message='Unable to parse JSON: {}'.format(e),
                                                      start=1,
                                                      end=1)
            )

    # Prepare Checks result
    if not an:
        conclusion = checks.Conclusion.SUCCESS
        summary = 'All JSON files passed this QC test.'
        details = None
    else:
        conclusion = checks.Conclusion.FAILURE
        summary = 'Not all JSON files passed this QC test.'
        details = 'Please look at the comments below and fix the outstanding problems.'

    # Update Check
    check.complete_check(token, conclusion=conclusion, summary=summary, details=details, annotations=an)
