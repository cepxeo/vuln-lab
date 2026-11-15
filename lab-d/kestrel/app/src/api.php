<?php
// The JSON API under /api/v1, called by the scripts of the quote and the
// password-reset pages.

function request_json(): array
{
    $data = json_decode((string) file_get_contents('php://input'), true);
    return is_array($data) ? $data : [];
}

// Partner rate comparison: fetch the partner's rate feed.
function api_rates_sync(): never
{
    $carrier = request_json()['carrier'] ?? null;
    $endpoint = is_array($carrier) && is_string($carrier['endpoint'] ?? null) ? $carrier['endpoint'] : '';
    $name = is_array($carrier) && is_string($carrier['name'] ?? null) ? $carrier['name'] : 'partner';
    if (!preg_match('#^https?://#i', $endpoint)) {
        json_out(['error' => 'carrier.endpoint must be an http(s) URL'], 400);
    }
    $host = strtolower((string) parse_url($endpoint, PHP_URL_HOST));
    if ($host === '') {
        json_out(['error' => 'carrier.endpoint has no host'], 400);
    }
    // D7: internal addresses are refused by the look of the host string. Other
    // spellings of the same address (2130706433, 0) are not on the list.
    foreach (['localhost', '127.', '10.', '192.168.', '169.254.'] as $blocked) {
        if (str_starts_with($host, $blocked)) {
            json_out(['error' => 'internal addresses are not allowed'], 400);
        }
    }
    $context = stream_context_create(['http' => ['timeout' => 3, 'follow_location' => 0, 'ignore_errors' => true]]);
    $body = @file_get_contents($endpoint, false, $context, 0, 4096);
    if ($body === false) {
        json_out(['carrier' => $name, 'status' => 'unreachable'], 502);
    }
    json_out(['carrier' => $name, 'status' => 'ok', 'sample' => mb_substr($body, 0, 600)]);
}

// Bulk quotes. The page sends JSON; the older XML form of the partner
// integration is still read.
function api_quote_bulk(): never
{
    $raw = (string) file_get_contents('php://input');
    $parcels = [];
    if (stripos((string) ($_SERVER['CONTENT_TYPE'] ?? ''), 'xml') !== false) {
        if (stripos($raw, 'file://') !== false) {
            json_out(['error' => 'unsupported document'], 400);
        }
        // D8: LIBXML_NOENT substitutes entities, external ones included. The
        // check above stops only the file:// spelling of a local path.
        $xml = @simplexml_load_string($raw, 'SimpleXMLElement', LIBXML_NOENT | LIBXML_NONET);
        if ($xml === false) {
            json_out(['error' => 'the document is not well-formed'], 400);
        }
        foreach ($xml->parcel as $parcel) {
            $parcels[] = ['to' => (string) $parcel->to, 'weight' => (string) $parcel->weight];
        }
        // A parsed document without <parcel> children says so, so a tester can
        // tell "parsed, wrong shape" from "not read at all" (a bare empty list
        // answered both before).
        if (!$parcels) {
            json_out(['error' => 'the document holds no <parcel> elements under its root'], 422);
        }
    } else {
        $data = json_decode($raw, true);
        $parcels = is_array($data) && is_array($data['parcels'] ?? null) ? $data['parcels'] : [];
    }
    $quotes = [];
    foreach (array_slice($parcels, 0, 50) as $parcel) {
        if (!is_array($parcel) || !is_scalar($parcel['to'] ?? null) || !is_numeric($parcel['weight'] ?? null)) {
            continue;
        }
        $quotes[] = ['to' => (string) $parcel['to'], 'weight' => (float) $parcel['weight'],
                     'price' => quote_price((float) $parcel['weight'])];
    }
    json_out(['quotes' => $quotes]);
}

// The second step of the password reset.
function api_reset_confirm(): never
{
    $input = request_json() ?: $_POST;
    $email = is_string($input['email'] ?? null) ? trim($input['email']) : '';
    $password = $input['password'] ?? null;
    $statement = db()->prepare('SELECT token FROM resets WHERE email = ? AND expires > ?');
    $statement->execute([$email, time()]);
    $reset = $statement->fetch();
    // D11: a loose comparison. JSON keeps the type of the value, and in PHP
    // true == "any non-empty string".
    if (!$reset || !(($input['token'] ?? null) == $reset['token'])) {
        json_out(['error' => 'the link is invalid or has expired'], 400);
    }
    if (!is_string($password) || strlen($password) < 12) {
        json_out(['error' => 'the password needs 12 characters or more'], 400);
    }
    db()->prepare('UPDATE users SET password_hash = ? WHERE email = ?')->execute([password_hash($password, PASSWORD_DEFAULT), $email]);
    db()->prepare('DELETE FROM resets WHERE email = ?')->execute([$email]);
    json_out(['ok' => true]);
}
