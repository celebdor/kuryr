==================================
DevStack Installation quick guide
==================================

This document is a quick guide to install `DevStack`_ the development
distribution of OpenStack, and configure it to support `Midonet` as
network provider. it assumes you have an Ubuntu distribution for your
OpenStack controller.

To install follow these steps:

First, get DevStack source code:

.. code-block:: bash

    $ git clone https://github.com/openstack-dev/devstack
    $ pushd devstack

Create a configuration file:

.. code-block:: bash
    $ cat >> local.conf << 'EOF'
    [[local|localrc]]
    OFFLINE=No
    RECLONE=No

    ENABLED_SERVICES=""

    Q_PLUGIN=midonet
    enable_plugin networking-midonet http://github.com/openstack/networking-midonet.git
    MIDONET_PLUGIN=midonet_v2
    MIDONET_CLIENT=midonet.neutron.client.api.MidonetApiClient
    MIDONET_USE_ZOOM=True
    Q_SERVICE_PLUGIN_CLASSES=midonet_l3
    NEUTRON_LBAAS_SERVICE_PROVIDERV1="LOADBALANCER:Midonet:midonet.neutron.services.loadbalancer.driver.MidonetLoadbalancerDriver:default"

    # hack for getting to internet from the containers
    sudo iptables -t nat -A POSTROUTING -s 172.24.4.1/24 -d 0.0.0.0/0 -j MASQUERADE

    # Credentials
    ADMIN_PASSWORD=pass
    DATABASE_PASSWORD=pass
    RABBIT_PASSWORD=pass
    SERVICE_PASSWORD=pass
    SERVICE_TOKEN=pass

    enable_service q-svc
    enable_service q-lbaas
    enable_service neutron
    enable_service key
    enable_service mysql
    enable_service rabbit
    enable_service horizon

    [[post-config|$NEUTRON_CONF_DIR/neutron_lbaas.conf]]
    [service_providers]
    service_provider = LOADBALANCER:Haproxy:neutron_lbaas.services.loadbalancer.drivers.haproxy.plugin_driver.HaproxyOnHostPluginDriver:default
    service_provider = LOADBALANCER:Midonet:midonet.neutron.services.loadbalancer.driver.MidonetLoadbalancerDriver

    # Log all output to files
    LOGFILE=$HOME/devstack.log
    SCREEN_LOGDIR=$HOME/logs
    EOF

Generate the installation:

.. code-block:: bash

    $ ./stack.sh

Once it finishes successfully, in order to verify that the haproxy load
balancer agent that we use for services is up and running, we source the
credentials and perform a neutron command:

.. code-block:: bash

    $ source openrc admin admin
    $ neutron agent-list -c agent_type -c host -c alive -c admin_state_up

    +--------------------+----------------+-------+----------------+
    | agent_type         | host           | alive | admin_state_up |
    +--------------------+----------------+-------+----------------+
    | Loadbalancer agent | ost-controller | :-)   | True           |
    +--------------------+----------------+-------+----------------+


.. _`DevStack`: http://docs.openstack.org/developer/devstack/

