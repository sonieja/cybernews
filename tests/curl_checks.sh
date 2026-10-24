#!/usr/bin/env bash
# tests/curl_checks.sh - quick security checks with curl against the RUNNING app.
# Start the app first (python web_app.py), then:  bash tests/curl_checks.sh
B=${BASE:-http://127.0.0.1:5000}
JAR=$(mktemp)
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
tok()  { curl -s -b "$JAR" -c "$JAR" "$B$1" | grep -o 'name="csrf_token" value="[^"]*"' | head -1 | cut -d'"' -f4; }

echo "== 1. Every public page answers 200 =="
for p in / /news /article/1 /login /register /contact /api/articles; do
  echo "$p -> $(code "$B$p")"
done
echo "/article/9999 -> $(code "$B/article/9999")   (404 = does not exist)"

echo "== 2. CSRF: POST /login WITHOUT a token =="
echo "status: $(code -X POST -d 'username=admin&password=x' "$B/login")   (400 = rejected)"

echo "== 3. SQL injection attempt in search =="
echo "q=' OR 1=1 --        -> $(curl -s -G "$B/api/articles" --data-urlencode "q=' OR 1=1 --")"
curl -s -G "$B/api/articles" --data-urlencode "q='; DROP TABLE articles; --" > /dev/null
echo "articles still in DB -> $(curl -s "$B/api/articles" | python3 -c 'import sys,json;print(len(json.load(sys.stdin)))')"

echo "== 4. Wrong password =="
T=$(tok /login)
echo "status: $(code -b "$JAR" -c "$JAR" -X POST --data-urlencode "csrf_token=$T" -d 'username=admin&password=guess123' "$B/login")   (401 = refused)"

echo "== 5. Normal user tries admin pages =="
U="curltester$RANDOM"
T=$(tok /register)
code -b "$JAR" -c "$JAR" -X POST --data-urlencode "csrf_token=$T" -d "username=$U&password=testpass123&confirm=testpass123" "$B/register" >/dev/null
T=$(tok /login)
code -b "$JAR" -c "$JAR" -X POST --data-urlencode "csrf_token=$T" -d "username=$U&password=testpass123" "$B/login" >/dev/null
for p in /admin /admin/articles/new /admin/audit-log; do
  echo "$U GET $p -> $(code -b "$JAR" "$B$p")   (403 = forbidden)"
done
rm -f "$JAR"
