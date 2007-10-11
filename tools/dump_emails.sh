#!/bin/sh

echo "select distinct email_address from luminotes_user_current;" | psql -U luminotes -A -t -q
