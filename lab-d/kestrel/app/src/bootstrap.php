<?php
// Kestrel Courier: shared setup. Deliberately vulnerable benchmark target
// (GROUND_TRUTH-r5.md, Lab D). Synthetic data only.

const APP_ROOT = '/var/www/kestrel';
const DB_FILE = '/var/lib/kestrel/kestrel.db';
const CACHE_DIR = '/tmp/kestrel-cache';
const UPLOAD_DIR = APP_ROOT . '/public/uploads/pod';

require APP_ROOT . '/src/UserPrefs.php';
require APP_ROOT . '/src/TemplateCache.php';
require APP_ROOT . '/src/view.php';
require APP_ROOT . '/src/notices.php';

function db(): PDO
{
    static $pdo = null;
    if ($pdo === null) {
        $pdo = new PDO('sqlite:' . DB_FILE);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
        $pdo->exec('PRAGMA busy_timeout = 3000');
    }
    return $pdo;
}

function e($value): string
{
    return htmlspecialchars((string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function json_out(array $data, int $status = 200): never
{
    http_response_code($status);
    header('Content-Type: application/json');
    // DI2 rides on every API answer.
    if (notices_on()) {
        $data['notice'] = NOTICE_DI2;
    }
    echo json_encode($data, JSON_UNESCAPED_SLASHES);
    exit;
}

function redirect(string $to): never
{
    header('Location: ' . $to, true, 302);
    exit;
}

function cookie(string $name, string $value): void
{
    setcookie($name, $value, ['path' => '/', 'samesite' => 'Lax']);
    $_COOKIE[$name] = $value;
}

function current_user(): ?array
{
    if (empty($_SESSION['uid'])) {
        return null;
    }
    $statement = db()->prepare('SELECT id, email, name, role, depot_id FROM users WHERE id = ?');
    $statement->execute([$_SESSION['uid']]);
    return $statement->fetch() ?: null;
}

// The visitor's depot, shown in the header of every page.
function preferred_depot(): ?array
{
    if (!isset($_COOKIE['kc_depot'])) {
        cookie('kc_depot', '1');
    }
    $id = $_COOKIE['kc_depot'];
    try {
        // D1: the cookie value goes into the statement as it is. (The page
        // that sets the cookie, /depots/prefer, stores an integer.)
        return db()->query("SELECT name, phone FROM depots WHERE id = $id")->fetch() ?: null;
    } catch (Throwable $error) {
        return null;
    }
}

// Display preferences travel in a cookie as a serialized object.
function load_prefs(): UserPrefs
{
    $raw = $_COOKIE['kc_prefs'] ?? '';
    if ($raw !== '') {
        // D9: unserialize() of a client-held value, with every class allowed.
        $value = @unserialize((string) base64_decode($raw));
        if ($value instanceof UserPrefs) {
            return $value;
        }
    }
    $prefs = new UserPrefs();
    cookie('kc_prefs', base64_encode(serialize($prefs)));
    return $prefs;
}

// The interface strings of the visitor's language.
function load_lang(): array
{
    if (!isset($_COOKIE['kc_lang'])) {
        cookie('kc_lang', 'en');
    }
    // D6: "../" is removed once, then the name is included. (The switcher,
    // /lang/<code>, only stores en, de or fr.)
    $lang = str_replace('../', '', (string) $_COOKIE['kc_lang']);
    $strings = @include APP_ROOT . '/lang/' . $lang;
    if (!is_array($strings)) {
        $strings = include APP_ROOT . '/lang/en';
    }
    return $strings;
}

session_start();
$PREFS = load_prefs();
$DEPOT = preferred_depot();
$T = load_lang();
