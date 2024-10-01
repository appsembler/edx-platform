#!/bin/bash

if [[ $DYNO == "mysql"* ]]; then
  # Start MySQL server in the background as the 'mysql' user
  echo "Starting MySQL..."
  chown -R mysql:mysql /var/lib/mysql
  su mysql -s /bin/bash -c "mysqld" &

  # Wait for MySQL to be ready
  until mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "SHOW DATABASES;" > /dev/null 2>&1; do
    echo "Waiting for MySQL to be ready..."
    sleep 5
  done

  # Initialize MySQL if the init script is available
  if [ -f /usr/local/bin/mysql-init.sh ]; then
    echo "Running MySQL init script..."
    /usr/local/bin/mysql-init.sh
  fi

  wait

elif [[ $DYNO == "rabbitmq"* ]]; then
  echo "Starting RabbitMQ..."
  rabbitmq-server &

  wait

elif [[ $DYNO == "memcache"* ]]; then
  echo "Starting Memcache..."
  memcached -u memcache &

  wait

else
  echo "No valid service specified."
fi
