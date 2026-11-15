#!/bin/sh
# Every start is a fresh lab: the database, the sessions, the uploads and the
# fragment cache are rebuilt from the seed.
set -e
rm -rf /var/lib/kestrel/* /tmp/kestrel-cache /var/www/kestrel/public/uploads
mkdir -p /var/lib/kestrel/sessions /tmp/kestrel-cache /var/www/kestrel/public/uploads/pod
php /usr/local/lib/kestrel-seed/seed.php
chown -R www-data:www-data /var/lib/kestrel /tmp/kestrel-cache /var/www/kestrel/public/uploads

# The internal carrier-key service: loopback only, reachable from this
# container alone (D7 reaches it through the site). Its own user: the file
# reads of the site (www-data) cannot open its source.
runuser -u kestrel-keys -- php -S 127.0.0.1:8081 /var/www/kestrel/internal/index.php >/dev/null 2>&1 &

exec apache2-foreground
