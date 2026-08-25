import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests


SCOPE = "wow.profile"


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    server_version = "WowProfileOAuth/1.0"

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        self.server.oauth_path = parsed.path
        self.server.oauth_code = params.get("code", [None])[0]
        self.server.oauth_state = params.get("state", [None])[0]
        self.server.oauth_error = params.get("error", [None])[0]
        self.server.oauth_error_description = params.get(
            "error_description", [None]
        )[0]

        if parsed.path != self.server.expected_path:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Unknown callback path.")
            return

        if self.server.oauth_error:
            body = (
                "Battle.net authorization failed. You can close this tab and "
                "return to the terminal."
            )
        else:
            body = (
                "Battle.net authorization complete. You can close this tab and "
                "return to the terminal."
            )

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, format, *args):
        return


def wait_for_authorization_code(config, hosts):
    redirect = urlparse(config["redirect_uri"])
    if redirect.scheme != "http" or redirect.hostname not in {"localhost", "127.0.0.1"}:
        raise RuntimeError(
            "BLIZZARD_REDIRECT_URI must be a localhost HTTP URL for local discovery."
        )

    port = redirect.port or 80
    expected_path = redirect.path or "/"
    state = secrets.token_urlsafe(24)

    server = HTTPServer((redirect.hostname, port), OAuthCallbackHandler)
    server.expected_path = expected_path
    server.oauth_code = None
    server.oauth_state = None
    server.oauth_error = None
    server.oauth_error_description = None
    server.oauth_path = None

    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "scope": SCOPE,
        "state": state,
    }
    auth_url = f"{hosts['oauth']}/authorize?{urlencode(params)}"

    print("Opening Battle.net authorization page in your browser...")
    print(auth_url)
    webbrowser.open(auth_url)

    server.timeout = 300
    started = time.monotonic()
    while server.oauth_code is None and server.oauth_error is None:
        if time.monotonic() - started > server.timeout:
            server.server_close()
            raise RuntimeError("Timed out waiting for Battle.net authorization callback.")
        server.handle_request()

    server.server_close()

    if server.oauth_error:
        description = server.oauth_error_description or server.oauth_error
        raise RuntimeError(f"Battle.net authorization failed: {description}")
    if server.oauth_path != expected_path:
        raise RuntimeError("Received OAuth callback on an unexpected path.")
    if server.oauth_state != state:
        raise RuntimeError("Received OAuth callback with an invalid state.")
    if not server.oauth_code:
        raise RuntimeError("Battle.net callback did not include an authorization code.")

    return server.oauth_code


def exchange_code_for_token(config, hosts, code):
    response = requests.post(
        f"{hosts['oauth']}/token",
        auth=(config["client_id"], config["client_secret"]),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config["redirect_uri"],
            "scope": SCOPE,
        },
        timeout=30,
    )
    response.raise_for_status()
    token = response.json()
    access_token = token.get("access_token")
    if not access_token:
        raise RuntimeError("Battle.net token response did not include an access token.")
    return access_token


def get_client_credentials_token(config, hosts):
    response = requests.post(
        f"{hosts['oauth']}/token",
        auth=(config["client_id"], config["client_secret"]),
        data={"grant_type": "client_credentials"},
        timeout=30,
    )
    response.raise_for_status()
    token = response.json()
    access_token = token.get("access_token")
    if not access_token:
        raise RuntimeError("Battle.net token response did not include an access token.")
    return access_token
