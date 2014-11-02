
RabbitMQ installation
~~~~~~~~~~~~~~~~~~~~~


# Ubuntu

sudo rabbitmqctl add_user oneflow PASSWORD
sudo rabbitmqctl add_vhost 1flow
sudo rabbitmqctl set_permissions -p 1flow oneflow ".*" ".*" ".*"
sudo rabbitmqctl set_user_tags oneflow management

sudo /usr/lib/rabbitmq/bin/rabbitmq-plugins enable rabbitmq_management
sudo service rabbitmq-server restart



# Arch Linux

IMPORTANT: take real care with /etc/hosts: localhost must be the last of the 127.0.0.1 line.

sudo -s
HOME=/var/lib/rabbitmq rabbitmqctl add_user oneflow PASSWORD
HOME=/var/lib/rabbitmq rabbitmqctl add_vhost 1flow
HOME=/var/lib/rabbitmq rabbitmqctl set_permissions -p 1flow oneflow ".*" ".*" ".*"
HOME=/var/lib/rabbitmq rabbitmqctl set_user_tags oneflow management
HOME=/var/lib/rabbitmq rabbitmq-plugins enable rabbitmq_management
