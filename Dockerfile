# Use the official MySQL image as a base
FROM mysql:8.0

ARG MYSQL_DATABASE
ARG MYSQL_USER
ARG MYSQL_PASSWORD
ARG MYSQL_ROOT_PASSWORD

# Copy the custom initialization and start scripts to the container
COPY ./mysql-init.sh /usr/local/bin/mysql-init.sh
COPY ./start.sh /usr/local/bin/start.sh

# Ensure the scripts have executable permissions
RUN chmod +x /usr/local/bin/mysql-init.sh
RUN chmod +x /usr/local/bin/start.sh

# Set environment variables for the new user
ENV MYSQL_DATABASE=$MYSQL_DATABASE
ENV MYSQL_USER=$MYSQL_USER
ENV MYSQL_PASSWORD=$MYSQL_PASSWORD
ENV MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD

# Expose port 3306 to allow connections to the database
EXPOSE 3306

# Start the MySQL server when the container is run
CMD ["/usr/local/bin/start.sh"]
