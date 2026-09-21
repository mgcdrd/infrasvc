#!/usr/bin/python3
#=============DO NOT EDIT - ANSIBLE CONTROLLED===============
# Minimal SigV4-signed S3 GET (path-style), stdlib only. Used by
# nginx-proxy-sync.sh because curl --aws-sigv4 is broken on Rocky 9's
# curl 7.76.
#
# Usage: nginx-proxy-sync-s3get.py <url> <out-file> <region> [ca-file]
# Credentials come from S3_ACCESS_KEY / S3_SECRET_KEY in the environment
# (not argv, so they never show up in `ps`). Prints the HTTP status (000 if
# the request itself failed); writes the body to <out-file> only on 200.
import datetime
import hashlib
import hmac
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request


def hmac_sha256(key, msg):
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def main():
    url, out, region = sys.argv[1:4]
    ca_file = sys.argv[4] if len(sys.argv) > 4 else None
    access_key = os.environ["S3_ACCESS_KEY"]
    secret_key = os.environ["S3_SECRET_KEY"]

    parts = urllib.parse.urlsplit(url)
    now = datetime.datetime.now(datetime.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date = amz_date[:8]
    payload_hash = hashlib.sha256(b"").hexdigest()

    canonical_uri = urllib.parse.quote(urllib.parse.unquote(parts.path) or "/", safe="/-_.~")
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = "\n".join([
        "GET",
        canonical_uri,
        "",
        "host:%s\nx-amz-content-sha256:%s\nx-amz-date:%s\n" % (parts.netloc, payload_hash, amz_date),
        signed_headers,
        payload_hash,
    ])
    scope = "%s/%s/s3/aws4_request" % (date, region)
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256",
        amz_date,
        scope,
        hashlib.sha256(canonical_request.encode()).hexdigest(),
    ])
    key = hmac_sha256(("AWS4" + secret_key).encode(), date)
    for part in (region, "s3", "aws4_request"):
        key = hmac_sha256(key, part)
    signature = hmac.new(key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    request = urllib.request.Request(url, headers={
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
        "Authorization": "AWS4-HMAC-SHA256 Credential=%s/%s, SignedHeaders=%s, Signature=%s"
                         % (access_key, scope, signed_headers, signature),
    })
    context = ssl.create_default_context(cafile=ca_file) if ca_file else None
    try:
        with urllib.request.urlopen(request, timeout=30, context=context) as response:
            body = response.read()
            code = response.status
    except urllib.error.HTTPError as err:
        print(err.code)
        return
    except Exception:
        print("000")
        return
    if code == 200:
        with open(out, "wb") as fh:
            fh.write(body)
    print(code)


main()
