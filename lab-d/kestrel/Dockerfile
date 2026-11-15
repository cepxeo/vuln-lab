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
# The comments that explain the planted flaws stay in the repository. They are
# removed from the image: the source is readable through the file-read flaws,
# and it must not give the other answers away.
RUN find /var/www/kestrel -name '*.php' -exec sed -i -E '/^[[:space:]]*\/\/( |$)/d' {} +
COPY entrypoint.sh /usr/local/bin/kestrel-entrypoint
RUN chmod +x /usr/local/bin/kestrel-entrypoint

EXPOSE 80
CMD ["kestrel-entrypoint"]
