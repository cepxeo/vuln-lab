<?php
// Internal carrier-key service: loopback only (started by entrypoint.sh).
header('Content-Type: application/json');
$path = strtok($_SERVER['REQUEST_URI'], '?');
if ($path === '/internal/keys') {
    echo json_encode([
        'service' => 'kestrel-carrier-keys',
        'northline_api_key' => 'KC-D07-19fa62c8',
        'eurodrop_api_key' => 'ed_live_synthetic_4410',
    ]);
    exit;
}
echo json_encode(['service' => 'kestrel-carrier-keys', 'paths' => ['/internal/keys']]);
