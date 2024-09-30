if [[ $DYNO == "mysql"* ]]; then
  # Start MySQL server in the background
  echo "Starting MySQL..."
  mysqld &

  # Wait for MySQL to be ready
  until mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "SHOW DATABASES;" > /dev/null 2>&1; do
    echo "Waiting for MySQL to be ready..."
    sleep 5
  done

#  /usr/local/bin/mysql-init.sh
  wait
elif  [[ $DYNO == "worker"* ]]; then
  echo "Starting worker..."
fi
elif  [[ $DYNO == "rabbitmq"* ]]; then
  echo "Starting RabbitMQ..."
fi
elif  [[ $DYNO == "memcache"* ]]; then
  echo "Starting memcache..."
fi
