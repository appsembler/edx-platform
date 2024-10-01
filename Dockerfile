# Use Python as the base image since the LMS likely needs Python
FROM python:3.8-slim

ARG MYSQL_DATABASE
ARG MYSQL_USER
ARG MYSQL_PASSWORD
ARG MYSQL_ROOT_PASSWORD

# Set environment variables
ENV MYSQL_DATABASE=$MYSQL_DATABASE
ENV MYSQL_USER=$MYSQL_USER
ENV MYSQL_PASSWORD=$MYSQL_PASSWORD
ENV MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD

# Install MySQL server, Memcached, and other required dependencies
RUN apt-get update && \
    apt-get install -y \
    default-mysql-server \
    default-mysql-client \
    memcached \
    rabbitmq-server \
    curl && \
    apt-get clean

# Copy custom scripts
COPY ./mysql-init.sh /usr/local/bin/mysql-init.sh
COPY ./start.sh /usr/local/bin/start.sh

# Add the permissions to copied scripts
RUN mkdir -p /run/mysqld && chown -R mysql:mysql /run/mysqld
RUN chmod +x /usr/local/bin/mysql-init.sh
RUN chmod +x /usr/local/bin/start.sh

# Expose the necessary ports for MySQL, Memcached, RabbitMQ, and LMS
EXPOSE 3306 11211 5672 8000

# Default command to start all services
CMD ["/usr/local/bin/start.sh"]
