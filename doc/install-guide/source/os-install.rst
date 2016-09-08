=========================
Installation in OpenStack
=========================

This document describes how to install Kuryr-Kubernetes using
instances provided by OpenStack.

This guide assumes you have OpenStack clients installed in your
computer.

Notice that in this guide you will make an OpenStack deployment
on top of an existing OpenStack infrastructure. This is required
due to the needed integration of OpenStack's Neutron with Midonet.

The procedure is a variation of the general procedure described
in the `Cloud Installation Guide <cloud-install.html>`_.
Only the relevant steps will be explained, so be sure you
read the guide before attempting a OpenStack-backed deployment.

Setup OS credentials
--------------------

Create the file *demo-openrc.sh* with the credentials given
to you by the OpenStack administrator.

.. code-block:: bash

   $ cat > demo-openrc.sh <<EOF
   export OS_USERNAME=<username>
   export OS_PASSWORD=<password>
   export OS_TENANT_NAME=<projectName>
   export OS_AUTH_URL=<auth url>
   EOF

Setup the required credentials and setup for the current session::

   $ . demo-openrc.sh

Additionally, to access the instances via ssh, you need to register a
key pair. If you haven't generate an ssh key pair, generate it first::

  $ssh-keygen

Now register the keys in OS::

  $ nova keypair-add --pub-key ~/.ssh/id_rsa.pub demo-key


Creating a network
------------------
Let's create a network for the instances that we'll use as the underlay for
this deployment::

    $ neutron net-create demo
    $ neutron subnet-create demo --name demo-sub \
      --gateway 10.142.0.254 --dns 8.8.8.8  10.142.0.0/24

Once it is created, we should allow ssh access to the instances in the
deployment, as well as communicaton between them:

.. code-block:: bash

   $ neutron security-group-create demo --description "security rules to access demo instances"
   $ nova secgroup-add-rule demo tcp 22 22 0.0.0.0/0
   $ nova secgroup-add-rule demo tcp 1 65535 10.142.0.0/24
   $ nova secgroup-add-rule demo udp 1 65535 10.142.0.0/24
   $ nova securoup-add-rule demo icmp -1 -1 10.142.0.0/24


Selecting Images and Flavors
----------------------------

Before you proceed creating the instances, it is importnat to select the right
instance images and the instance flavors that will be used for the different
components.

First, list the images:

.. code-block:: bash

    $ nova image-list

    +--------------------------------------+------------------------------+--------+
    | ID                                   | Name                         | Status |
    +--------------------------------------+------------------------------+--------+
     ...
    | 10a70cf6-28ac-440c-9e76-8b8fdc21c08e | CoreOS 1068.6.0              | ACTIVE |
     ....
    | fc1e589e-3d68-4f36-a76e-c01b9fd5f332 | Ubuntu 14.04.3 20151216      | ACTIVE |
     ...
    +--------------------------------------+------------------------------+--------+

The different instances (ost-controller, k8s-controller, k8s-workers) will have
different `resource requirements <intallation.html#requirements>`_. List available flavors and select those that best
match those requirements:

.. code-block:: bash

    $ nova flavor-list

     +----+-----------+-----------+------+-----------+------+-------+-------------+-----------+
     | ID | Name      | Memory_MB | Disk | Ephemeral | Swap | VCPUs | RXTX_Factor | Is_Public |
     +----+-----------+-----------+------+-----------+------+-------+-------------+-----------+
     ...
     | 12 | m2.large  | 8193      | 20   | 0         |      | 2     | 1.0         | True      |
     ...
     |  7 | m2.xlarge | 16384     | 80   | 0         |      | 4     | 1.0         | True      |
     ...
     | 5  | m1.xlarge | 16384     | 80   | 0         |      | 8     | 1.0         | True      |
     ...
     +----+-----------+-----------+------+-----------+------+-------+-------------+-----------+


Preparing for accessing instances
---------------------------------

To complete the installation procedure, you will need to access the instances you create. in order to do so,
you will have to assign a floating ip from a public network. Ask your OpenStack administrator for this network
and be sure you have the rights to assign floating-ips from it.

You must follow the following steps for each instance, once you create it:

First, create a floating ip:

.. code-block:: bash

     $ neutron floatingip-create <external network>
     Created a new floatingip:
     +---------------------+--------------------------------------+
     | Field               | Value                                |
     +---------------------+--------------------------------------+
     | fixed_ip_address    |                                      |
     | floating_ip_address | <floating ip address>                |
     | floating_network_id | c0ccd5d3-f5fa-4608-9310-49919038faa4 |
     | id                  | e5d39a05-ecd4-41bc-a104-93b798dfc644 |
     | port_id             |                                      |
     | router_id           |                                      |
     | status              | ACTIVE                               |
     | tenant_id           | bbefc5080f814a46bd1b1103ea83750a     |
     +---------------------+--------------------------------------+

Take note of the ip address, as you will need it later to connect to the instance.

Now we can associate the floating ip address with the instance:

.. code-block:: bash

   $ nova floating-ip-associate <instance> <floating ip address>

Finally, to access the instance, use its floating ip and the key-pair you generated.
Notice that for CoreOS instances, the root username is "core".

.. code-block:: bash

    $ ssh core@<flating ip>
    CoreOS stable (1122.2.0)
    Last login: Wed Jul 7 13:14:16 2016 from 62.37.161.182

Creating OST Controller instance
--------------------------------

First, edit the :download:`cloud-config-ost-controller.yaml<./cloud-config-ost-controller.yaml>` as described in the `Cloud installation guide <cloud-install.html#ost-config>`_.

Let's provision an instance for the OST Controller

.. code-block:: bash

    $ nova boot --flavor m2.xlarge --image "CoreOS 1068.6.0"  \
           --nic net-name=demo,v4-fixed-ip=10.142.0.2 \
           --security-group demo --key-name demo-key ost-controller \
           --user-data cloud-config-ost-controller.yaml

    +--------------------------------------+-----------------------------------------------+
    | Property                             | Value                                         |
    +--------------------------------------+-----------------------------------------------+
    ...
    | created                              | 2016-07-13T13:46:48Z                          |
    | flavor                               | m2.xlarge (12)                                |
    | hostId                               |                                               |
    | id                                   | 6e308df3-1312-4286-98e9-b5166ed2d19a          |
    | image                                | CoreOS (10a70cf6-28ac-440c-9e76-8b8fdc21c08e) |
    | key_name                             | demo-key                                      |
    | metadata                             | {}                                            |
    | name                                 | ost-controller                                |
    | os-extended-volumes:volumes_attached | []                                            |
    | progress                             | 0                                             |
    | security_groups                      | demo                                          |
    | status                               | BUILD                                         |
    | tenant_id                            | bbefc5080f814a46bd1b1103ea83750a              |
    | updated                              | 2016-07-13T13:46:40Z                          |
    | user_id                              | 337002c9ef774525a03dfd8da88662df              |
    +--------------------------------------+-----------------------------------------------+


Login into the ost-controller instance and follow the same post-installation steps defined in
the installation guide.


Kubernetes controller
---------------------

Edit the :download:`cloud-config-k8s-controller.yaml <./cloud-config-k8s-controller.yaml>` file
according to the `Cloud Installation Guide <cloud-install.html#k8s-config>`_.

Then create the controller instance:

.. code-block:: bash

    $ nova boot --flavor m2.large --image "CoreOS 1068.6.0"  \
           --nic net-name=demo,v4-fixed-ip=10.142.0.3 \
           --security-group demo --key-name demo-key k8s-controller \
           --user-data cloud-config-k8s-controller.yaml

    +--------------------------------------+-----------------------------------------------+
    | Property                             | Value                                         |
    +--------------------------------------+-----------------------------------------------+
    ...
    | created                              | 2016-07-13T13:56:48Z                          |
    | flavor                               | m2.large (12)                                 |
    | hostId                               |                                               |
    | id                                   | 518d5174-c012-4ba7-b137-4fbb53d54c1e          |
    | image                                | CoreOS (10a70cf6-28ac-440c-9e76-8b8fdc21c08e) |
    | key_name                             | demo-key                                      |
    | metadata                             | {}                                            |
    | name                                 | k8s-controller                                |
    | os-extended-volumes:volumes_attached | []                                            |
    | progress                             | 0                                             |
    | security_groups                      | demo                                          |
    | status                               | BUILD                                         |
    | tenant_id                            | bbefc5080f814a46bd1b1103ea83750a              |
    | updated                              | 2016-07-13T13:56:49Z                          |
    | user_id                              | 337002c9ef774525a03dfd8da88662df              |
    +--------------------------------------+-----------------------------------------------+

Login into the k8s-controller instance and follow the same post-installation steps defined in
the installation guide.


Worker nodes
------------

Edit the :download:`cloud-config-k8s-worker.yaml <./cloud-config-k8s-worker.yaml>` file
according to the `Cloud Installation Guide <cloud-install.html#worker-config>`_:


Using this cloud-config file you can create as many worker instances as you decide:

.. code-block:: bash

    $ nova boot --flavor m1.large --image "CoreOS 1068.6.0"  \
           --nic net-name=demo,v4-fixed-ip=10.142.0.4 \
           --security-group demo --key-name demo-key k8s-worker1 \
           --user-data cloud-config-k8s-worker.yaml

    +--------------------------------------+-----------------------------------------------+
    | Property                             | Value                                         |
    +--------------------------------------+-----------------------------------------------+
    ...
    | created                              | 2016-07-13T14:16:49Z                          |
    | flavor                               | m1.xlarge (5)                                 |
    | hostId                               |                                               |
    | id                                   | c551d6a6-49d0-4f9a-9998-57adbc810e04          |
    | image                                | CoreOS (10a70cf6-28ac-440c-9e76-8b8fdc21c08e) |
    | key_name                             | demo-key                                      |
    | metadata                             | {}                                            |
    | name                                 | k8s-worker1                                   |
    | os-extended-volumes:volumes_attached | []                                            |
    | progress                             | 0                                             |
    | security_groups                      | demo                                          |
    | status                               | BUILD                                         |
    | tenant_id                            | bbefc5080f814a46bd1b1103ea83750a              |
    | updated                              | 2016-07-13T14:16:50Z                          |
    | user_id                              | 337002c9ef774525a03dfd8da88662df              |
    +--------------------------------------+-----------------------------------------------+

Login into the k8s-worker instance and follow the same post-installation steps defined in
the installation guide.



Post-Installation
-----------------
Now you can go to the `Installation guide <installation.html#post_install>`_ and continue with the installation procedure.
