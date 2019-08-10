from flask import Flask, make_response, request

import example
import signature

__author__ = "@Wietze"
__copyright__ = "Copyright 2019"

app = Flask(__name__)


@app.before_request
def require_valid_token():
    if not request.headers.get('X-HUB-SIGNATURE') or not signature.verify_signature(request):
        return make_response("", 403)


@app.route("/hook", methods=["POST"])
def message_actions():
    github_request = request.get_json()
    if github_request.get('action'):
        if github_request.get('action') in ['requested', 'rerequested']:
            example.run_test(github_request)
        return make_response("", 201)
    return make_response("", 500)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port='443', ssl_context=('cert.pem', 'key.pem'))
