<?php
// The staff area (after sign-in) and the administration page.

function require_staff(): array
{
    $user = current_user();
    if (!$user) {
        redirect('/login');
    }
    return $user;
}

function page_staff(): never
{
    $user = require_staff();
    $statement = db()->prepare('SELECT id, day FROM manifests WHERE depot_id = ? ORDER BY day DESC');
    $statement->execute([$user['depot_id']]);
    $links = '';
    foreach ($statement as $manifest) {
        $links .= '<li><a href="/staff/manifest?m=' . md5((string) $manifest['id']) . '">Manifest of ' . e($manifest['day']) . '</a></li>';
    }
    page('Staff desk', '<p>Signed in as ' . e($user['name']) . ' (' . e($user['email']) . ').</p>'
        . '<h2>Your depot\'s manifests</h2><ul>' . $links . '</ul>'
        . '<h2>Proof of delivery</h2><p><a href="/staff/pod/upload">Upload a delivery photo</a></p>');
}

function page_staff_manifest(): never
{
    require_staff();
    $wanted = (string) ($_GET['m'] ?? '');
    // D13: a manifest is found by the MD5 of its number, and the reader's
    // depot is never compared with the manifest's.
    foreach (db()->query('SELECT id, depot_id, day, body FROM manifests') as $manifest) {
        if (hash_equals(md5((string) $manifest['id']), $wanted)) {
            page('Manifest of ' . $manifest['day'], '<pre class="mail">' . e($manifest['body']) . '</pre><p><a href="/staff">Back</a></p>');
        }
    }
    not_found();
}

function page_staff_upload(): never
{
    require_staff();
    $note = '';
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_FILES['photo']) && $_FILES['photo']['error'] === UPLOAD_ERR_OK) {
        $name = basename((string) $_FILES['photo']['name']);
        $extension = strtolower(pathinfo($name, PATHINFO_EXTENSION));
        // D12: a blocklist of script extensions. The web server also runs
        // .phtml (conf/kestrel.conf), which is not on it.
        if ($name === '' || $name[0] === '.' || in_array($extension, ['php', 'php5', 'phar'], true)) {
            $note = '<p class="error">This file type is not accepted.</p>';
        } elseif ($_FILES['photo']['size'] > 512 * 1024) {
            $note = '<p class="error">The photo is larger than 512 KB.</p>';
        } else {
            move_uploaded_file($_FILES['photo']['tmp_name'], UPLOAD_DIR . '/' . $name);
            $note = '<p class="note">Stored as <a href="/uploads/pod/' . e(rawurlencode($name)) . '">/uploads/pod/' . e($name) . '</a>.</p>';
        }
    }
    page('Proof of delivery', $note . '<form method="post" enctype="multipart/form-data" class="stack">'
        . '<label>Shipment reference <input name="shipment"></label>'
        . '<label>Photo <input name="photo" type="file"></label><button>Upload</button></form>');
}

function page_admin_settings(): never
{
    require_staff();
    // D14: the role is read from the kc_role cookie, which is only base64.
    if (base64_decode((string) ($_COOKIE['kc_role'] ?? '')) !== 'admin') {
        page('Administration', '<p>Only administrators can open this page.</p>', 403);
    }
    $rows = '';
    foreach (db()->query("SELECT k, value FROM settings WHERE k LIKE 'carrier_%' ORDER BY k") as $setting) {
        $rows .= '<tr><th>' . e($setting['k']) . '</th><td><code>' . e($setting['value']) . '</code></td></tr>';
    }
    page('Administration', '<h2>Carrier accounts</h2><table>' . $rows . '</table>');
}
