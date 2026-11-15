<?php
// Kestrel Courier: the front controller. Every address that is not a file in
// this folder arrives here (FallbackResource in conf/kestrel.conf).
require __DIR__ . '/../src/bootstrap.php';
require APP_ROOT . '/src/pages.php';
require APP_ROOT . '/src/api.php';
require APP_ROOT . '/src/staff.php';

$path = rawurldecode((string) strtok($_SERVER['REQUEST_URI'], '?'));
$post = $_SERVER['REQUEST_METHOD'] === 'POST';

if (preg_match('#^/depots/region/(.+)$#s', $path, $match)) {
    page_depots_region($match[1]);
}
if (preg_match('#^/lang/([a-z]{2})$#', $path, $match)) {
    page_lang($match[1]);
}
if (preg_match('#^/_outbox/(\d+)$#', $path, $match)) {
    page_outbox((int) $match[1]);
}

switch (rtrim($path, '/') ?: '/') {
    case '/': page_home();
    case '/track': page_track();
    case '/depots': page_depots();
    case '/depots/search': page_depots_search();
    case '/depots/prefer': page_depots_prefer();
    case '/quote': page_quote();
    case '/labels': page_labels();
    case '/label/download': page_label_download();
    case '/reviews': page_reviews();
    case '/contact': page_contact();
    case '/go': page_go();
    case '/login': page_login();
    case '/logout': page_logout();
    case '/account/forgot': page_forgot();
    case '/account/reset': page_reset();
    case '/_outbox': page_outbox(null);
    case '/staff': page_staff();
    case '/staff/manifest': page_staff_manifest();
    case '/staff/pod/upload': page_staff_upload();
    case '/admin':
    case '/admin/settings': page_admin_settings();
    case '/api/v1/rates/sync': $post ? api_rates_sync() : json_out(['error' => 'POST only'], 405);
    case '/api/v1/quote/bulk': $post ? api_quote_bulk() : json_out(['error' => 'POST only'], 405);
    case '/api/v1/account/reset/confirm': $post ? api_reset_confirm() : json_out(['error' => 'POST only'], 405);
    case '/api/v1/audit/collect': notice_bait('DI2');
    case '/robots.txt': page_robots();
}
not_found();
