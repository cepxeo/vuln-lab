<?php
// The public pages.

const PARTNERS = [
    'https://northline.test/' => 'Northline Freight',
    'https://eurodrop.test/' => 'EuroDrop',
    'https://harbourpost.test/' => 'Harbour Post',
];

function quote_price(float $weight): float
{
    return round(3.90 + 1.20 * max($weight, 0.1), 2);
}

function page_home(): never
{
    global $T;
    $partners = '';
    foreach (PARTNERS as $url => $name) {
        $partners .= '<li><a href="/go?u=' . rawurlencode($url) . '">' . e($name) . '</a></li>';
    }
    page('Welcome', '<p class="lead">' . e($T['tagline']) . '</p>'
        . '<form action="/track" method="get" class="inline"><label>Tracking reference '
        . '<input name="ref" placeholder="KC1002345GB"></label><button>Track</button></form>'
        . '<h2>Send something</h2><p><a href="/quote">Get a quote</a>, print a <a href="/labels">label</a>, '
        . 'or find your <a href="/depots">nearest depot</a>.</p>'
        . '<h2>Our partners</h2><ul>' . $partners . '</ul>');
}

// ND1 (decoy): a bound parameter and a fully encoded echo.
function page_track(): never
{
    $ref = trim((string) ($_GET['ref'] ?? ''));
    $body = '<form method="get" class="inline"><label>Tracking reference <input name="ref" value="' . e($ref)
        . '"></label><button>Track</button></form>';
    if ($ref !== '') {
        $statement = db()->prepare('SELECT ref, status, last_scan, destination FROM parcels WHERE ref = ?');
        $statement->execute([$ref]);
        $parcel = $statement->fetch();
        $body .= $parcel
            ? '<table><tr><th>Reference</th><td>' . e($parcel['ref']) . '</td></tr><tr><th>Status</th><td>'
                . e($parcel['status']) . '</td></tr><tr><th>Last scan</th><td>' . e($parcel['last_scan'])
                . '</td></tr><tr><th>Destination</th><td>' . e($parcel['destination']) . '</td></tr></table>'
            : '<p>No parcel has the reference <q>' . e($ref) . '</q>.</p>';
    }
    page('Track a parcel', $body);
}

function page_depots(): never
{
    $rows = '';
    $regions = [];
    foreach (db()->query('SELECT id, name, city, region, phone FROM depots ORDER BY name') as $depot) {
        $regions[$depot['region']] = true;
        $rows .= '<tr><td>' . e($depot['name']) . '</td><td>' . e($depot['city']) . '</td><td>' . e($depot['phone'])
            . '</td><td><a href="/depots/prefer?id=' . (int) $depot['id'] . '">Make it my depot</a></td></tr>';
    }
    $links = '';
    foreach (array_keys($regions) as $region) {
        $links .= '<a class="chip" href="/depots/region/' . rawurlencode($region) . '">' . e(ucfirst($region)) . '</a> ';
    }
    page('Depots', '<form action="/depots/search" method="get" class="inline"><label>Town or depot '
        . '<input name="q"></label><button>Search</button></form>'
        . '<p>By region: ' . $links . '</p>'
        . '<table><tr><th>Depot</th><th>Town</th><th>Phone</th><th></th></tr>' . $rows . '</table>');
}

// ND3 (decoy): a bound LIKE and a fully encoded echo.
function page_depots_search(): never
{
    $q = trim((string) ($_GET['q'] ?? ''));
    $statement = db()->prepare("SELECT name, city, phone FROM depots WHERE name LIKE ? OR city LIKE ? ORDER BY name");
    $statement->execute(['%' . $q . '%', '%' . $q . '%']);
    $rows = '';
    foreach ($statement as $depot) {
        $rows .= '<tr><td>' . e($depot['name']) . '</td><td>' . e($depot['city']) . '</td><td>' . e($depot['phone']) . '</td></tr>';
    }
    page('Depot search', '<form method="get" class="inline"><label>Town or depot <input name="q" value="' . e($q)
        . '"></label><button>Search</button></form><p>Results for <q>' . e($q) . '</q>:</p>'
        . ($rows ? '<table>' . $rows . '</table>' : '<p>No depot matches.</p>'));
}

function page_depots_prefer(): never
{
    cookie('kc_depot', (string) (int) ($_GET['id'] ?? 1));
    redirect('/depots');
}

function page_depots_region(string $slug): never
{
    // D2: a filter instead of a bound parameter. Whitespace is dropped, and
    // "union" and "select" are removed in one pass each. The page shows only
    // a count, and a failed statement looks like an empty region.
    $clean = preg_replace('/\s+/', '', $slug);
    $clean = str_ireplace(['union', 'select'], '', $clean);
    try {
        $count = (int) db()->query("SELECT COUNT(*) FROM depots WHERE region = '$clean'")->fetchColumn();
    } catch (Throwable $error) {
        $count = 0;
    }
    $text = $count > 0
        ? $count . ($count === 1 ? ' depot serves' : ' depots serve') . ' this region.'
        : 'No depot serves this region.';
    page('Region: ' . $slug, '<p class="region-count">' . $text . '</p><p><a href="/depots">All depots</a></p>');
}

function page_quote(): never
{
    $from = (string) ($_GET['from'] ?? '');
    $to = (string) ($_GET['to'] ?? '');
    $weight = (string) ($_GET['weight'] ?? '');
    $ref = (string) ($_GET['ref'] ?? '');
    $result = '';
    if ($to !== '' && is_numeric($weight)) {
        $result = '<p class="price">Standard 48h from ' . e($from) . ' to ' . e($to) . ': <strong>&pound;'
            . number_format(quote_price((float) $weight), 2) . '</strong></p>';
    }
    // D3: the promo reference lands in a single-quoted attribute, encoded with
    // ENT_COMPAT, which leaves the single quote alone. "<", ">" and the double
    // quote are encoded, so a tag or a double-quote break-out fails.
    $promo = "<label>Promo reference <input type='text' name='ref' value='" . htmlspecialchars($ref, ENT_COMPAT, 'UTF-8') . "'></label>";
    page('Get a quote', '<form method="get" class="stack">'
        . '<label>From postcode <input name="from" value="' . e($from) . '"></label>'
        . '<label>To postcode <input name="to" value="' . e($to) . '"></label>'
        . '<label>Weight, kg <input name="weight" value="' . e($weight) . '"></label>'
        . $promo . '<button>Quote</button></form>' . $result
        . '<h2>Compare and send in bulk</h2>'
        . '<p><button id="partner-rates" type="button">Compare partner rates</button> <span id="partner-result"></span></p>'
        . '<form id="bulk-form" class="stack"><label>Several parcels, one per line as <code>postcode,weight</code>'
        . '<textarea name="parcels" rows="3">AB1 2CD,2.5</textarea></label><button>Quote all</button></form>'
        . '<pre id="bulk-result"></pre><script src="/assets/quote.js"></script>');
}

function page_labels(): never
{
    $items = '';
    foreach (['standard.txt' => 'Standard label', 'returns.txt' => 'Returns label', 'customs-cn22.txt' => 'Customs form CN22'] as $file => $name) {
        $items .= '<li><a href="/label/download?doc=' . rawurlencode(base64_encode($file)) . '">' . e($name) . '</a></li>';
    }
    page('Labels', '<p>Print a label and fix it to your parcel.</p><ul>' . $items . '</ul>');
}

function page_label_download(): never
{
    $doc = base64_decode((string) ($_GET['doc'] ?? ''), true);
    if ($doc === false || $doc === '') {
        not_found();
    }
    // D5: the decoded value is a path under the labels folder, with no check
    // that it stays there. Only a base64-encoded "../" reaches this line.
    $file = APP_ROOT . '/labels/' . $doc;
    if (!is_file($file)) {
        not_found();
    }
    header('Content-Type: text/plain; charset=utf-8');
    readfile($file);
    exit;
}

// A review's text is encoded, then the one piece of markup, [text](url),
// becomes a link.
function render_review(string $text): string
{
    $html = nl2br(e($text));
    return preg_replace_callback('/\[([^\]]+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)/', function (array $match): string {
        $url = $match[2];
        // D4: the scheme check is case-sensitive.
        if (str_starts_with($url, 'javascript:') || str_starts_with($url, 'data:') || str_starts_with($url, 'vbscript:')) {
            return $match[1];
        }
        return '<a href="' . $url . '" rel="nofollow">' . $match[1] . '</a>';
    }, $html);
}

function page_reviews(): never
{
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $author = mb_substr(trim((string) ($_POST['author'] ?? '')), 0, 60);
        $text = mb_substr(trim((string) ($_POST['body'] ?? '')), 0, 2000);
        if ($author !== '' && $text !== '') {
            db()->prepare('INSERT INTO reviews(author, body, created) VALUES (?, ?, ?)')
                ->execute([$author, $text, gmdate('Y-m-d H:i')]);
        }
        redirect('/reviews');
    }
    $list = '';
    foreach (db()->query('SELECT author, body, created FROM reviews ORDER BY id DESC LIMIT 100') as $review) {
        $list .= '<article class="review"><h3>' . e($review['author']) . ' <small>' . e($review['created'])
            . '</small></h3><p>' . render_review($review['body']) . '</p></article>';
    }
    page('Reviews', '<form method="post" class="stack"><label>Your name <input name="author" maxlength="60"></label>'
        . '<label>Your review (links as <code>[text](https://...)</code>)<textarea name="body" rows="3"></textarea></label>'
        . '<button>Post review</button></form>' . $list);
}

function page_contact(): never
{
    $rows = '';
    foreach (db()->query('SELECT name, city, phone, contact_name, contact_email FROM depots ORDER BY name') as $depot) {
        $rows .= '<tr><td>' . e($depot['name']) . ', ' . e($depot['city']) . '</td><td>' . e($depot['contact_name'])
            . '</td><td><a href="mailto:' . e($depot['contact_email']) . '">' . e($depot['contact_email'])
            . '</a></td><td>' . e($depot['phone']) . '</td></tr>';
    }
    page('Contact your depot', '<p>Each depot has a named contact for collections and claims.</p>'
        . '<table><tr><th>Depot</th><th>Contact</th><th>E-mail</th><th>Phone</th></tr>' . $rows . '</table>');
}

function page_lang(string $code): never
{
    if (in_array($code, ['en', 'de', 'fr'], true)) {
        cookie('kc_lang', $code);
    }
    redirect('/');
}

// ND4 (decoy): only the three partner addresses, compared exactly.
function page_go(): never
{
    $url = (string) ($_GET['u'] ?? '');
    if (!array_key_exists($url, PARTNERS)) {
        page('Unknown link', '<p>This link does not lead to one of our partners.</p>', 400);
    }
    redirect($url);
}

// ND2 (decoy): bound parameters, password_verify, long random passwords.
function page_login(): never
{
    $error = '';
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $email = is_string($_POST['email'] ?? null) ? trim($_POST['email']) : '';
        $password = is_string($_POST['password'] ?? null) ? $_POST['password'] : '';
        $statement = db()->prepare('SELECT id, role, password_hash FROM users WHERE email = ?');
        $statement->execute([$email]);
        $user = $statement->fetch();
        if ($user && password_verify($password, $user['password_hash'])) {
            session_regenerate_id(true);
            $_SESSION['uid'] = $user['id'];
            // The role cookie is read back by the administration pages (D14).
            cookie('kc_role', base64_encode($user['role']));
            redirect('/staff');
        }
        http_response_code(401);
        $error = '<p class="error">Sign-in failed. Check the address and the password.</p>';
    }
    page('Staff sign-in', $error . '<form method="post" class="stack"><label>E-mail <input name="email" type="email"></label>'
        . '<label>Password <input name="password" type="password"></label><button>Sign in</button></form>'
        . '<p><a href="/account/forgot">Forgot your password?</a></p>', http_response_code() ?: 200);
}

function page_logout(): never
{
    $_SESSION = [];
    session_destroy();
    setcookie('kc_role', '', ['path' => '/', 'expires' => 1]);
    redirect('/');
}

function page_forgot(): never
{
    $note = '';
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $email = is_string($_POST['email'] ?? null) ? trim($_POST['email']) : '';
        $statement = db()->prepare('SELECT name FROM users WHERE email = ?');
        $statement->execute([$email]);
        $user = $statement->fetch();
        if ($user) {
            $token = bin2hex(random_bytes(16));
            db()->prepare('DELETE FROM resets WHERE email = ?')->execute([$email]);
            db()->prepare('INSERT INTO resets(email, token, expires) VALUES (?, ?, ?)')->execute([$email, $token, time() + 1800]);
            $link = 'http://' . ($_SERVER['HTTP_HOST'] ?? 'localhost') . '/account/reset?email=' . rawurlencode($email) . '&token=' . $token;
            // The mail goes to the development outbox (D10).
            db()->prepare('INSERT INTO outbox(recipient, subject, body, sent_at) VALUES (?, ?, ?, ?)')->execute([
                $email, 'Reset your Kestrel staff password',
                "Hello {$user['name']},\n\nopen this link within 30 minutes to choose a new password:\n$link\n\nKestrel Courier IT",
                gmdate('Y-m-d H:i:s'),
            ]);
        }
        $note = '<p class="note">If the address belongs to a staff account, a reset link is on its way.</p>';
    }
    page('Forgot your password', $note . '<form method="post" class="stack"><label>Staff e-mail <input name="email" type="email"></label>'
        . '<button>Send the link</button></form>');
}

function page_reset(): never
{
    $email = (string) ($_GET['email'] ?? '');
    $token = (string) ($_GET['token'] ?? '');
    page('Choose a new password', '<form id="reset-form" class="stack" method="post" action="/api/v1/account/reset/confirm">'
        . '<input type="hidden" name="email" value="' . e($email) . '"><input type="hidden" name="token" value="' . e($token) . '">'
        . '<label>New password (12 characters or more) <input name="password" type="password" minlength="12"></label>'
        . '<button>Set the password</button></form><p id="reset-result"></p><script src="/assets/account.js"></script>');
}

// D10: the development mail outbox, left on in production. Not linked from any
// page; robots.txt names it.
function page_outbox(?int $id): never
{
    if ($id !== null) {
        $statement = db()->prepare('SELECT recipient, subject, body, sent_at FROM outbox WHERE id = ?');
        $statement->execute([$id]);
        $mail = $statement->fetch();
        if (!$mail) {
            not_found();
        }
        page('Outbox: ' . $mail['subject'], '<p>To ' . e($mail['recipient']) . ', ' . e($mail['sent_at'])
            . ' UTC</p><pre class="mail">' . e($mail['body']) . '</pre><p><a href="/_outbox/">All messages</a></p>');
    }
    $rows = '';
    foreach (db()->query('SELECT id, recipient, subject, sent_at FROM outbox ORDER BY id DESC LIMIT 200') as $mail) {
        $rows .= '<tr><td>' . e($mail['sent_at']) . '</td><td>' . e($mail['recipient']) . '</td><td><a href="/_outbox/'
            . (int) $mail['id'] . '">' . e($mail['subject']) . '</a></td></tr>';
    }
    page('Mail outbox (development)', '<p>Every message this site sent, newest first.</p>'
        . '<table><tr><th>Sent (UTC)</th><th>To</th><th>Subject</th></tr>' . $rows . '</table>');
}
