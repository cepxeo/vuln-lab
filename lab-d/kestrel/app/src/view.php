<?php
// The page frame.

function footer_depots(): string
{
    $cache = new TemplateCache('footer-depots');
    $html = $cache->get();
    if ($html === null) {
        $html = '';
        foreach (db()->query('SELECT name, city FROM depots ORDER BY name') as $depot) {
            $html .= '<li>' . e($depot['name']) . ', ' . e($depot['city']) . '</li>';
        }
        $cache->put($html);
    }
    return $html;
}

function page(string $title, string $body, int $status = 200): never
{
    global $T, $DEPOT, $PREFS;
    http_response_code($status);
    $theme = $PREFS->theme === 'dark' ? 'dark' : 'light';
    $depot = $DEPOT
        ? 'Your depot: <strong>' . e($DEPOT['name']) . '</strong> &middot; ' . e($DEPOT['phone'])
        : 'Choose your depot on the <a href="/depots">depots page</a>.';
    $user = current_user();
    $account = $user
        ? '<a href="/staff">' . e($user['name']) . '</a> &middot; <a href="/logout">Sign out</a>'
        : '<a href="/login">' . e($T['nav_signin']) . '</a>';
    $nav = '';
    foreach (['/track' => 'nav_track', '/depots' => 'nav_depots', '/quote' => 'nav_quote', '/labels' => 'nav_labels',
              '/reviews' => 'nav_reviews', '/contact' => 'nav_contact'] as $href => $key) {
        $nav .= '<a href="' . $href . '">' . e($T[$key]) . '</a>';
    }
    echo '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        . '<meta name="viewport" content="width=device-width, initial-scale=1">'
        . '<title>' . e($title) . ' | Kestrel Courier</title>'
        . '<link rel="stylesheet" href="/assets/site.css"></head>'
        . '<body class="' . $theme . '">'
        . '<header><a class="brand" href="/">Kestrel Courier</a><nav>' . $nav . '</nav>'
        . '<span class="account">' . $account . '</span></header>'
        . '<div class="depot-bar">' . $depot
        . '<span class="langs"><a href="/lang/en">EN</a> <a href="/lang/de">DE</a> <a href="/lang/fr">FR</a></span></div>'
        . '<main><h1>' . e($title) . '</h1>' . $body . '</main>'
        . '<footer><p>' . e($T['tagline']) . '</p><ul class="depots">' . footer_depots() . '</ul>'
        . '<p class="small">Kestrel Courier Ltd. A demonstration site with synthetic data.</p></footer>'
        . '</body></html>';
    exit;
}

function not_found(): never
{
    page('Page not found', '<p>There is no page at this address.</p>', 404);
}
