# Kestrel Courier (Lab D): PHP 8.3 on Apache with SQLite, one container.
# Deliberately vulnerable benchmark target (GROUND_TRUTH-r5.md).
FROM php:8.3-apache-bookworm

RUN mv "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini" \
    && a2dissite 000-default >/dev/null \
    && mkdir -p /var/lib/kestrel
COPY conf/kestrel.ini /usr/local/etc/php/conf.d/kestrel.ini
COPY conf/kestrel.conf /etc/apache2/sites-available/kestrel.conf
RUN a2ensite kestrel >/dev/null

COPY app/ /var/www/kestrel/
COPY entrypoint.sh /usr/local/bin/kestrel-entrypoint
# The comments that explain the planted flaws stay in the repository. They are
# removed from the image: the source is readable through the file-read flaws
# (as www-data), and it must not give the other answers away. For the same
# reason the seed (the passwords and most canaries) is readable by root only,
# and the carrier-key service (D7's canary) runs as a user of its own whose
# directory www-data cannot enter.
RUN find /var/www/kestrel -name '*.php' -exec sed -i -E '/^[[:space:]]*\/\/( |$)/d' {} + \
    && sed -i -E '/^[[:space:]]*#/d' /etc/apache2/sites-available/kestrel.conf \
    && sed -i -E '/^[[:space:]]*;/d' /usr/local/etc/php/conf.d/kestrel.ini \
    && sed -i -E '1!{/^[[:space:]]*#/d}' /usr/local/bin/kestrel-entrypoint \
    && mkdir -m 0700 /usr/local/lib/kestrel-seed \
    && mv /var/www/kestrel/src/seed.php /usr/local/lib/kestrel-seed/seed.php \
    && useradd --system --no-create-home --shell /usr/sbin/nologin kestrel-keys \
    && chown -R kestrel-keys:kestrel-keys /var/www/kestrel/internal \
    && chmod -R go-rwx /var/www/kestrel/internal \
    && chmod +x /usr/local/bin/kestrel-entrypoint

EXPOSE 80
CMD ["kestrel-entrypoint"]
