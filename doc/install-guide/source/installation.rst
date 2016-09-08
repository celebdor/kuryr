=============================
Kuryr-Kubernetes Installation
=============================

This document describes how to install and test Kuryr-Kubernetes.

In this guide, we will refer to three different environments, which
can be physical or virtual: the OpenStack controler node (ost-controller),
the Kubernetes cluster controller (k8s-controller) and one or more Kubernetes
workers (k8s-worker1, k8s-worker2, ...).

Even if you have an existing Openstack setup, it is advisable that you
install the ost-controller to a have a clean start and ease the
installation and test procedures.

Please notice this guide will install a Kubernetes controller node.
This is required even if you have a running cluster, due to the needed
integration of Kuryr with Kuberlets.

To facilitate the installation process, we provide the scripts to configure
the k8s nodes (controller and workers) using `coreos-cloudinit`_ utility.

These files can be used to configure nodes provisioned from cloud providers.
The `Cloud Installation Guide <cloud-install.html>`_ explains how to adapt this
installation guide when using in cloud. This is particularly interesting when
launching multiple worker nodes.

.. _requirements:

Requirements
------------

This installation guide assumes the following requirements for the installation
environment:

The nodes run the stable release of CoreOS (1068.10.0 or later).

The actual physical resources required by each node depend on the workload
you plan to execute. Following are some recomendations:

==============   ====       ======
Node             CPUs       Memory
==============   ====       ======
ost-controller   4          16Gb
k8s-controller   4          8Gb
k8s-worker       8          8Gb
==============   ====       ======

This guide assumes that you have `Docker`_ installed in all nodes.

Finally, this guide assumes all nodes have connectivity between them and
access to the Internet for package installation.

.. _ost-install:

OpenStack controller
--------------------

The configuration file :download:`cloud-config-ost.yaml<./cloud-config-ost.yaml>` automates
the deployment of an OpenStack Neutron controller node integrated with Midonet.
It installs and configures the supporting services such as MariadDB, Cassandra,
Zookeeper, and RabbitMQ.

The installation process uses the configuration parameters defined in the
*/etc/conf.d/ost-controller-defaults* file which is part of the cloud config file:

.. code-block:: yaml

    write-files:
    ...
      - path: /etc/conf.d/ost-controller-defaults
        permissions: '0644'
        content: |
          DB_HOST=127.0.0.1
          DB_USERNAME=root
          DB_PASSWORD=root
          OS_DEBUG=True
          OS_VERBOSE=Fals4
          DB_NAME=openstack
          OS_TOKEN=admin
          OS_AUTH_URL=http://127.0.0.1:35357/v2.0
          OS_AUTH_URI=http://127.0.0.1:5000/v2.0
          OS_NEUTRON_URL=http://127.0.0.1:9696
          OS_USERNAME=neutron
          OS_PASSWORD=neutron
          OS_RPC_BACKEND=rabbit
          RB_HOST=127.0.0.1
          RB_USERNAME=guest
          RB_PASSWORD=guest
          OS_TENANT_NAME=service
          OS_REGION_NAME=RegionOne
          MN_CLUSTER_URL=http://127.0.0.1:8181/midonet-api
          MN_TUNNEL_ZONE=demo
          MN_USERNAME=admin
          MN_PASSWORD=admin
          MN_PROJECT=admin
          ZK_QUORUM="127.0.0.1:1"
          ZK_CLUSTER="127.0.0.1:2181"
          ZK_ID=1
          C_SERVERS="127.0.0.1"
          C_FACTOR=1

In general, the values provided in the file can be left untouched, but they can be easily  overriden
if you create an initial */etc/conf.d/ost-controller* file. The installation process merges both
files, giving precedense to the values provided by you.

For example, the local IP can be provided as follows:

.. code-block:: bash

   $ mkdir /etc/conf.d
   $ cat >> /etc/conf.d/ost-controller <<EOF
     LOCAL_IP=10.142.0.2
     EOF

To proceed deploying and configuring the components run the coreos-cloudinit command:

.. code-block:: bash

    $ coreos-cloudinit --from-file cloud-config-ost.yaml
    2016/08/22 23:22:52 Checking availability of "local-file"
    2016/08/22 23:22:52 Fetching user-data from datasource of type "local-file"
    2016/08/22 23:22:52 Fetching meta-data from datasource of type "local-file"
    2016/08/22 23:22:52 Parsing user-data as cloud-config
    2016/08/22 23:22:52 Merging cloud-config from meta-data and user-data
    2016/08/22 23:22:52 Writing file to "/etc/conf.d/ost-controller-defaults"
    2016/08/22 23:22:52 Wrote file to "/etc/conf.d/ost-controller-defaults"
    2016/08/22 23:22:52 Wrote file /etc/conf.d/ost-controller-defaults to filesystem
    2016/08/22 23:22:52 Writing file to "/opt/bin/neutron"
    2016/08/22 23:22:52 Wrote file to "/opt/bin/neutron"
    2016/08/22 23:22:52 Wrote file /opt/bin/neutron to filesystem
    2016/08/22 23:22:52 Writing file to "/opt/bin/prepare-config"
    .
    .
    .
    2016/08/22 23:22:53 Result of "start" on "keystone.service": done
    2016/08/22 23:22:53 Calling unit command "start" on "neutron.service"'
    2016/08/22 23:22:53 Result of "start" on "neutron.service": done
    2016/08/22 23:22:53 Calling unit command "start" on "neutron-lbaas.service"'
    2016/08/22 23:22:57 Result of "start" on "neutron-lbaas.service": done
    2016/08/22 23:22:57 Calling unit command "start" on "midonet-agent.service"'
    2016/08/22 23:22:57 Result of "start" on "midonet-agent.service": done
    2016/08/22 23:22:57 Calling unit command "start" on "midonet-cluster.service"'
    2016/08/22 23:23:14 Result of "start" on "midonet-cluster.service": done

.. _ost-post-install:

Post-installation configuration
+++++++++++++++++++++++++++++++

After the installation process fineshes, it is necessary to create the users and
service endpoints in Keystone, using the script created by the installation process:

.. code-block:: bash

    $ /opt/bin/keystone-provisioning.sh
    +-------------+----------------------------------+
    | Field       | Value                            |
    +-------------+----------------------------------+
    | description | None                             |
    | enabled     | True                             |
    | id          | 822505779e514e6d8746b4f33e26e4a5 |
    | name        | admin                            |
    +-------------+----------------------------------+
    +-------+----------------------------------+
    | Field | Value                            |
    +-------+----------------------------------+
    | id    | 6ae2e49a00c342fdaeb17d13daf767d2 |
    | name  | admin                            |
    +-------+----------------------------------+
    | name        | service                          |
    +-------------+----------------------------------+
    | name        | keystone                         |
    | type        | identity                         |
    +-------------+----------------------------------+
    .
    .
    .
    +--------------+----------------------------------+
    | adminurl     | http://127.0.0.1:9696            |
    | id           | 4d45f85304dc4f298401ff23c7320924 |
    | internalurl  | http://127.0.0.1:9696            |
    | publicurl    | http://127.0.0.1:9696            |
    | region       | RegionOne                        |
    | service_id   | 0d255909e555431b8ef2f770df62e247 |
    | service_name | neutron                          |
    | service_type | network                          |
    +--------------+----------------------------------+

Finally, we need to create one Midonet tunnel zone to allow the communication between the K8s
workers and the service load balancing agent, running in the ost-controller.

.. code-block:: bash

   $ sudo /opt/bin/midonet-setup
   zone 33102da5-a7a7-43b7-b904-a46faecb0f1b host 5a1bb683-704f-4ce9-8c38-45a8ec174b41 address 192.168.1.124


.. _K8s-install:

Kubernetes controller
---------------------

The configuration file :download:`cloud-config-k8s-controller.yaml<./cloud-config-k8s-controller.yaml>` automates the deployment
of all the components required by the kubernetes controller. In this process, the Kuryr contanier
is downloaded and installed as a *systemctl* service using the `Docker image from Midonet project<https://hub.docker.com/r/midonet/raven/>`::

    [Unit]
    Description=Kuryr Kubernetes API watcher and translator of events to \
      Neutron entities.
    Documentation=https://github.com/midonet/kuryr/tree/k8s
    Requires=kube-apiserver.service docker.service
    After=kube-apiserver.service docker.service

    [Service]
    EnvironmentFile=/etc/conf.d/k8s-controller
    ExecStartPre=/opt/bin/wupiao ${K8S_CONTROLLER}:8080
    ExecStartPre=-/usr/bin/docker kill %n
    ExecStartPre=-/usr/bin/docker rm %n
    ExecStart=/usr/bin/docker run --name %n \
      -e SERVICE_CLUSTER_IP_RANGE=10.0.0.0/24 \
      -e SERVICE_USER=${OS_USERNAME} \
      -e SERVICE_TENANT_NAME=${OS_TENANT_NAME} \
      -e SERVICE_PASSWORD=${OS_PASSWORD} \
      -e IDENTITY_URL=http://${OST_CONTROLLER}:35357/v2.0 \
      -e OS_URL=http://${OST_CONTROLLER}:9696 \
      -e K8S_API=http://${K8S_CONTROLLER}:8080 \
      -v /var/log/kuryr:/var/log/kuryr \
      midonet/raven:0.5.2
    ExecStop=/usr/bin/docker kill %n
    ExecStopPost=/usr/bin/docker rm -f %n
    Restart=no
    RestartSec=3

The installation process uses the */etc/conf.d/k8s-controller* file to hold configuration
information. Create it and add the information about the IP for the ost-controller node and the
k8s-controller node itself:

.. code-block:: bash

   $ mkdir /etc/conf.d
   $ cat >> /etc/conf.d/k8s-controller <<EOF
     LOCAL_IP=10.142.0.3
     OST_CONTROLLER=10.142.0.2
     EOF

You can also modify any of the default parameters defined in the */etc/conf.d/k8s-controller-defaults*
file in the *write-file* section of the cloud-config file

.. code-block:: yaml

    write-files:
      -path: /etc/conf.d/k8s-controller-defaults
       #Default configuration parameters
       content: |
         OS_USERNAME=neutron
         OS_PASSWORD=neutron
         OS_TENANT_NAME=service

Now, proceed to deploy and configure the components:

.. code-block:: bash

    $ coreos-cloudinit --from-file cloud-config-k8s-controller.yaml
    2016/08/03 09:18:39 Checking availability of "local-file"
    2016/08/03 09:18:39 Fetching user-data from datasource of type "local-file"
    2016/08/03 09:18:39 Fetching meta-data from datasource of type "local-file"
    2016/08/03 09:18:39 Parsing user-data as cloud-config
    .
    .
    .
    2016/08/03 09:19:01 Result of "start" on "demo-prepare-cli-tools.service": done
    2016/08/03 09:19:01 Calling unit command "start" on "etcd3.service"'
    2016/08/03 09:19:04 Result of "start" on "etcd3.service": done
    2016/08/03 09:19:04 Calling unit command "start" on "fleet.service"'
    2016/08/03 09:19:04 Result of "start" on "fleet.service": done
    2016/08/03 09:19:04 Calling unit command "start" on "docker.service"'
    2016/08/03 09:19:04 Result of "start" on "docker.service": done
    2016/08/03 09:19:04 Calling unit command "start" on "kubernetes-setup-files.service"'
    2016/08/03 09:19:29 Result of "start" on "kubernetes-setup-files.service": done
    2016/08/03 09:19:29 Calling unit command "start" on "kube-apiserver.service"'
    2016/08/03 09:19:29 Result of "start" on "kube-apiserver.service": done
    2016/08/03 09:19:29 Calling unit command "start" on "kube-controller-manager.service"'
    2016/08/03 09:19:42 Result of "start" on "kube-controller-manager.service": done
    2016/08/03 09:19:42 Calling unit command "start" on "kube-scheduler.service"'
    2016/08/03 09:19:42 Result of "start" on "kube-scheduler.service": done
    2016/08/03 09:19:42 Calling unit command "start" on "kuryr-watcher.service"'
    2016/08/03 09:19:42 Result of "start" on "kuryr-watcher.service": done


.. _worker-install:

Kubernetes Workers
------------------

Similarly to the k8s-controller, the K8s workers can be configured with a
cloud-config file :download:`cloud-config-k8s-worker.yaml<cloud-config-k8s-worker.yaml>`. The same file can be used for multiple workers.

The installation process intalls the `Midonet's flavor of Kubelet<https://hub.docker.com/r/midonet/kubelet/>`, the Kubernetes worker service, which has the required integration with Kuryr::

    [Unit]
    Description=Kubernetes kubelet with kuryr CNI driver and MidoNet \
                port binding tool
    Documentation=https://github.com/midonet/midonet-docker
    Requires=docker.service prepare-config.service
    After=docker.service prepare-config.service

    [Service]
    ...
    ExecStart=/usr/bin/docker run --name %n \
          -e MASTER_IP=${K8S_CONTROLLER} \
          -e ZK_ENDPOINTS=${OST_CONTROLLER}:2181 \
          -e UUID="${UUID}" \
          --volume=/:/rootfs:ro \
          --volume=/sys:/sys:ro \
          --volume=/var/lib/docker/:/var/lib/docker:rw \
          --volume=/var/lib/kubelet/:/var/lib/kubelet:rw \
          --volume=/var/run:/var/run:rw \
          --volume=/var/log/kuryr:/var/log/kuryr \
          --net=host \
          --privileged=true \
          --pid=host \
          midonet/kubelet

The installation script expects some configuration information in the
*/etc/conf.d/k8s-worker* file. The IP addresses of the openstack and k8s controllers
are needed. Also, the ip address to be used for joining the  tunnel zone defined
in the ost-controller:

Create it and complete the required information:

.. code-block:: bash

   $ mkdir /etc/conf.d
   $ cat >> /etc/conf.d/k8s-worker <<EOF
    OST_CONTROLLER=10.142.0.2
    K8S_CONTROLLER=10.142.0.3
    LOCAL_IP=10.142.0.4
    EOF

Now, proceed to deploy and configure the components:

.. code-block:: bash

    $ coreos-cloudinit --from-file cloud-config-k8s-worker.yaml
      2016/08/03 10:49:24 Checking availability of "local-file"
      2016/08/03 10:49:24 Fetching user-data from datasource of type "local-file"
      2016/08/03 10:49:24 Fetching meta-data from datasource of type "local-file"
      2016/08/03 10:49:24 Parsing user-data as cloud-config
      .
      .
      .
      2016/08/03 10:49:24 Calling unit command "start" on "prepare-config.service"'
      2016/08/03 10:49:25 Result of "start" on "prepare-config.service": done
      2016/08/03 10:49:25 Calling unit command "start" on "midonet-agent.service"'
      2016/08/03 10:51:46 Result of "start" on "midonet-agent.service": done
      2016/08/03 10:51:46 Calling unit command "start" on "kubelet.service"'
      2016/08/03 10:53:12 Result of "start" on "kubelet.service": done

.. _k8s-worker-setup:

Setup
+++++

Once the installation process ends, run the midonet setup script to join the tunnel zone
and allow communication between workers and the open stack controller node:

.. code-block:: bash

    $ /opt/bin/midonet-setup.sh

The previous steps can be repeated for each worker. The rest of this document assumes you
have at least two workers.


.. _post-installation:

Post-Installation
-----------------

Once the instances are installed, some post-installation setup is required.


Connecting ost-controller to Raven External Network
+++++++++++++++++++++++++++++++++++++++++++++++++++

We will use the ost-controller as external host to test the access to services.
It is necesary to configure your network so that the ost-controller has access
to the service network.

Kuryr `automatically creates an external network for services<../../en/ops-guide/getting_started.html#neutron-topology>`_ `raven-default-external-net` and
a subnet for the default namespace `raven-default-external-subnet`. By deafult
this subnet is assigned the range 172.16.0.0/16 for external addresses (FIPs).

The fitst step is to create an uplink at the ost-controller, using the script provided in
the installation. See `Edge Router Setup at the Midonet Quick Start Guide <https://docs.midonet.org/docs/latest-en/quick-start-guide/ubuntu-1404_liberty/content/edge_router_setup.html>`_ for more details.

.. code-block:: bash

    $ sudo /opt/bin/create_uplink
    Created a new router:
    +-----------------------+--------------------------------------+
    | Field                 | Value                                |
    +-----------------------+--------------------------------------+
    | admin_state_up        | True                                 |
    | external_gateway_info |                                      |
    | id                    | a8b55de2-5b6c-4de1-bae2-a8a954146434 |
    | name                  | mn-edge                              |
    | routes                |                                      |
    | status                | ACTIVE                               |
    | tenant_id             | 75067bca32054921a657e53a1cffdbec     |
    +-----------------------+--------------------------------------+
    .
    .
    .
    Added interface 2d087d3f-fdd0-4228-a048-b1c6ede1649a to router mn-edge.
    Updated router: mn-edge

Then, create an interface to link the ost-controller host with Raven's default services subnet:

.. code-block:: bash

    $ sudo /opt/bin/link_raven_network
    Added interface 56d9ab50-e527-4fcb-884b-a51ae02dddb4 to router af96d950-97aa-473f-87a3-328830a5f774

It should be possible to reach the gateway of the default service network:

.. code-block:: bash

    $ ping -c 3 172.16.0.1
    PING 172.16.0.1 (172.16.0.1) 56(84) bytes of data.
    64 bytes from 172.16.0.1: icmp_seq=1 ttl=64 time=4.56 ms
    64 bytes from 172.16.0.1: icmp_seq=2 ttl=64 time=3.61 ms
    64 bytes from 172.16.0.1: icmp_seq=3 ttl=64 time=3.49 ms

   --- 172.16.0.1 ping statistics ---
   3 packets transmitted, 3 received, 0% packet loss, time 2002ms
   rtt min/avg/max/mdev = 3.498/3.892/4.566/0.481 ms

.. _post-installiation-verification:

Post-installation verification
------------------------------

Checking Health
+++++++++++++++

From the k8s-controller node check that the nodes are up:

.. code-block:: bash

    $ kubectl get nodes
    NAME                                            STATUS    AGE
    k8s-worker1.c.my_gce_project_name.internal      Ready     13h
    k8s-worker2.c.my_gce_project_name.internal      Ready     13h

If you see both of your workers, that's good. Then we check that all the
services are running:

.. code-block:: bash

    $ sudo systemctl status kube-scheduler
    ● kube-scheduler.service - Kubernetes Scheduler
       Loaded: loaded (/etc/systemd/system/kube-scheduler.service; static;
       vendor preset: disabled)
          Active: active (running) since Wed 2016-07-06 17:13:38 UTC; 20h ago
    $ sudo systemctl status kube-controller-manager
    ● kube-controller-manager.service - Kubernetes Controller Manager
       Loaded: loaded (/etc/systemd/system/kube-controller-manager.service; static; vendor preset: disabled)
       Active: active (running) since Wed 2016-07-06 17:13:33 UTC; 20h ago
    $ sudo systemctl status kuryr-watcher
    ● kuryr-watcher.service - Kuryr Kubernetes API watcher
       Loaded: loaded (/etc/systemd/system/kuryr-watcher.service; static; vendor preset: disabled)
       Active: active (running) since Wed 2016-07-06 21:46:02 UTC; 15h ago

If you see it as active, even though some *ExecStartPre* or *ExecStop* processes
may be exited in failure, it is in a healthy state. This is because these
failed tasks are there to clean up things and will fail if there is nothing to
clean up.

Running your first containers
+++++++++++++++++++++++++++++

With all the cluster healthy, let's run our first containers:

.. code-block:: bash

    $ kubectl run --image nginx --replicas 2 my-nginx
    deployment "my-nginx" created

After a moment, they should show as running:

.. code-block:: bash

    $ kubectl get pods
    NAME                        READY     STATUS    RESTARTS   AGE
    my-nginx-1830394127-mazlo   1/1       Running   0          24s
    my-nginx-1830394127-uyh8d   1/1       Running   0          24s

Once they is running, we can get their IPs:

.. code-block:: bash

    $ kubectl exec my-nginx-1830394127-mazlo -- ip -4 a show dev eth0
    15: eth0@if16: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default qlen 1000
        inet 192.168.0.14/24 scope global eth0
           valid_lft forever preferred_lft forever
    $ kubectl exec my-nginx-1830394127-uyh8d -- ip -4 a show dev eth0
    21: eth0@if22: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default qlen 1000
        inet 192.168.0.6/24 scope global eth0
           valid_lft forever preferred_lft forever

Having seen the ips, let's verify connectivity:

.. code-block:: bash

    $ kubectl exec my-nginx-1830394127-uyh8d ping 192.168.0.14


Exposing your services to the external world
++++++++++++++++++++++++++++++++++++++++++++

Now that we have deployed the pods, we will expose them as a service and show how they can
be accessed from an external network. In order to do so, we will use the same ost-controller
node as external node, as it is not part of the cluster of workers.

From the k8s-controller instance, create a service to expose the pods with and ip
address obtained from external network:

.. code-block:: bash

    $ kubectl expose deployment my-nginx --external-ip 172.16.0.12 --port=80
    service "my-nginx" exposed

    $ kubectl get services my-nginx
    kubectl get services
    NAME         CLUSTER-IP   EXTERNAL-IP   PORT(S)   AGE
    my-nginx     10.0.0.137   172.16.0.12   80/TCP    11s


You can check this association has also been made in neutron:

.. code-block:: bash

    $ neutron floatingip-list -c fixed_ip_address -c floating_ip_address
    +------------------+---------------------+
    | fixed_ip_address | floating_ip_address |
    +------------------+---------------------+
    | 10.0.0.137       | 172.16.0.12         |
    +------------------+---------------------+

if you follwed the post intallation procedure and created a link to Raven's external network,
the service should now be accessible from the ost-controller instance::

   $ wget 172.16.0.12 -nv --method=HEAD
        2016-07-27 13:42:36 URL: http://172.16.0.12/ 200 OK


.. _`Midonet`: https://www.midonet.org/
.. _`coreos-cloudinit`: https://coreos.com/os/docs/latest/cloud-config.html
.. _`Docker`: https://docs.docker.com/engine/installation/linux/
