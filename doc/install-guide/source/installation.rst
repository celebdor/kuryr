=============================
Kuryr-Kubernetes Installation
=============================

This document describes how to install and test Kuryr-Kubernetes.
It assumes you have a running installation of OpenStack's Neutron
using `Midonet`_ as network providers. If not, see `DevStack Installation`_
for a quick guide to install and configure `DevStack`_ the development
version of OpenStack.

In this guide, we will refer to three different environments, which
can be physical or virtual: the OpenStack controller node (ost-controller),
the Kubernetes cluster control1er (k8s-controller) and one or more Kubernetes
workers (k8s-worker1, k8s-worker2, ...).

This guide assumes that you have `Docker`_ installed in the Kubernetes
nodes (controller and workers).

To facilitate the installation process, we provide the scripts to configure
the k8s nodes (controller and workers) using `coreos-cloudinit`_ utility.
Refer to the `CoreOS Cloud Init Installation`_ for  instructions on how to
install it.

Finally, this guide assumes all nodes have connectivity between them and
access to the Internet for package installation.


OpenStack controller
--------------------

At the ost-controller, the only step needed is to create one midonet
tunnel zone to allow the communication between the K8s workers and the
service load balancing agent, running in the ost-controller.

First, create the tunnel-zone:

.. code-block:: bash

    $ midonet-cli -e tunnel-zone create name demo type vxlan
      282d7315-382c-4736-a567-afa57009d942

The name used is important because the k8s-workers will add themselves to it
based on this name.

With the uuid for the tunnel zone that was returned, we should proceed to
add the ost-controller host to the tunnel zone. This will allow the haproxy
loadbalancer agent to communicate with the pods in the worker instances.

Check your host uuid:

.. code-block:: bash

    $ midonet-cli -e host list
    host bd6a3fe1-a655-49af-bd77-d3b2a5356af4 name ost-controller alive true addresses fe80:0:0:0:0:11ff:fe00:1101,169.254.123.1,fe80:0:0:0:4001:aff:fe8e:2,10.142.0.2,172.17.0.1,fe80:0:0:0:fc6c:38ff:fe47:f864,127.0.0.1,0:0:0:0:0:0:0:1,fe80:0:0:0:0:11ff:fe00:1102,fe80:0:0:0:c4fd:6dff:fe99:7a6d,172.19.0.2 flooding-proxy-weight 1 container-weight 1 container-limit no-limit enforce-container-limit false

Then add it to the tunnel zone, using the internal IP:

.. code-block:: bash

    $ midonet-cli -e tunnel-zone 282d7315-382c-4736-a567-afa57009d942 add \
      member host bd6a3fe1-a655-49af-bd77-d3b2a5356af4 address 10.142.0.2
    zone 282d7315-382c-4736-a567-afa57009d942 host bd6a3fe1-a655-49af-bd77-d3b2a5356af4 address 10.142.0.2


Kubernetes controller
---------------------

The configuration file :download:`cloud-config-k8s-controller.yaml<./cloud-config-k8s-controller.yaml>` automates the deployment
of all the components required by the kubernetes controller. In this process, the Kuryr contanier
is downloaded and installed as a *systemctl* service::

    [Unit]
    Description=Kuryr Kubernetes API watcher and translator of events to \
      Neutron entities.
    Documentation=https://github.com/midonet/kuryr/tree/k8s
    Requires=kube-apiserver.service docker.service
    After=kube-apiserver.service docker.service

    [Service]
    EnvironmentFile=/etc/conf.d/k8s-master
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
k8s-controller node itself, as well as the credentials to access Openstack services:

.. code-block:: bash

   $ mkdir /etc/conf.d
   $ cat >> /etc/conf.d/k8s-controller <<EOF
     OST_CONTROLLER_IP=10.142.0.2
     K8S_CONTROLLER_IP=10.142.0.3
     OS_USERNAME=admin
     OS_PASSWORD=admin
     OS_TENANT_NAME=admin
     EOF

Now, proceed to deploy and configure the components:

.. code-block:: bash

    $ coreos-cloudinit --from-file cloud-config-k8s-controller.yaml


Kubernetes Workers
------------------

Similarly to the k8s-controller, the K8s workers can be configured with a
cloud-config file :download:`cloud-config-k8s-worker.yaml<cloud-config-k8s-worker.yaml>`. The same file can be used for multiple workers.

The installation process intalls the Midonet's flavor of Kubelet, the Kubernetes worker service, which has
the required integration with Kuryr::

    [Unit]
    Description=Kubernetes kubelet with kuryr CNI driver and MidoNet \
                port binding tool
    Documentation=https://github.com/midonet/midonet-docker
    Requires=docker.service prepare-config.service
    After=docker.service prepare-config.service

    [Service]
    EnvironmentFile=/etc/conf.d/k8s-worker
    ExecStartPre=/usr/bin/docker pull midonet/kubelet
    ExecStartPre=/opt/bin/wupiao ${K8S_CONTROLLER}:8080
    ExecStartPre=-/usr/bin/docker kill %n
    ExecStartPre=-/usr/bin/docker rm %n
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
    ExecStop=/usr/bin/docker kill %n
    ExecStopPost=/usr/bin/docker rm -f %n
    Restart=always
    RestartSec=3
    After=midonet-agent.service

The installation script expects some configuration information in the
*/etc/conf.d/k8s-worker* file. The IP addresses of the openstack and k8s controllers
are needed. Also, to automate the setup, the name of the tunnel zone defined
in the OpenStack controller, as well as the local ip for the worker.

Create it and complete the required information:

.. code-block:: bash

   $ mkdir /etc/conf.d
   $ cat >> /etc/conf.d/k8s-worker <<EOF
    OST_CONTROLLER_IP=10.142.0.2
    K8S_CONTROLLER_IP=10.142.0.3
    LOCAL_IP=10.142.0.4
    TUNNEL_ZONE=demo
    EOF

Now, proceed to deploy and configure the components:

.. code-block:: bash

    $ coreos-cloudinit --from-file cloud-config-k8s-worker.yaml

Once the installation process ends, run the midonet setup script to join the tunnel zone
and allow communication between workers and the open stack controller node:

.. code-block:: bash

    $ /opt/bin/midonet-setup.sh

The previous steps can be repeated for each worker. The rest of this document assumes you
have at least two workers.

Checking Health
---------------

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
-----------------------------

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


Exposing a service
------------------

Now that se have the pods deployed, we will expose them as a service and show how they can
be accessed from an external network. In order to do so, we will use the same ost-controller
node as external node, as it is not part of the cluster of workers.

Kuryr creates automatically an external network for services `raven-default-external-net` and
a subnet for the default namespace `raven-default-external-subnet`. For the purpose of this demo,
it is necessary that this subnet be accessible from the ost-controller host.

First,create an interface to link the ost-controller's network with Raven's default services subnet:

.. code-block:: bash

    $ neutron router-interface-add $(neutron router-list  | awk '$4=="mn-edge" {print $2}') $(neutron subnet-list | awk '$4=="raven-default-external-subnet" {print $2}')
    Added interface 56d9ab50-e527-4fcb-884b-a51ae02dddb4 to router af96d950-97aa-473f-87a3-328830a5f774

Secondly, create the appropiated routes:

.. code-block:: bash

    $ ip -4 route add 172.16.0.0/16 via 172.19.0.1 dev mn-uplink-host
    $ iptables -t nat -A POSTROUTING -s 172.16.0.0/16 -j MASQUERADE

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

Exposing your services to the external world
--------------------------------------------

From the k8s-controller instance, create a service to expose the pods with and ip
address obtained from external network:

.. code-block:: bash

    $ kubectl expose deployment my-nginx --external-ip 172.16.0.12 --port=80
    service "my-nginx" exposed

    $ kubectl get services my-nginx
    kubectl get services
    NAME         CLUSTER-IP   EXTERNAL-IP   PORT(S)   AGE
    my-nginx     10.0.0.137   172.16.0.12   80/TCP    11s


You can check this association has also be made in neutron:

.. code-block:: bash

    $ neutron floatingip-list -c fixed_ip_address -c floating_ip_address
    +------------------+---------------------+
    | fixed_ip_address | floating_ip_address |
    +------------------+---------------------+
    | 10.0.0.137       | 172.16.0.12         |
    +------------------+---------------------+

The service should now be accessible from the ost-controller instance:

.. code-block:: bash

   $ wget 172.16.0.12 -nv --method=HEAD
     2016-07-27 13:42:36 URL: http://172.16.0.12/ 200 OK


.. _`DevStack Installation`: ./devstack.html
.. _`DevStack`: http://docs.openstack.org/developer/devstack/
.. _`Midonet`: https://www.midonet.org/
.. _`coreos-cloudinit`: https://coreos.com/os/docs/latest/cloud-config.html
.. _`Docker`: https://docs.docker.com/engine/installation/linux/
.. _`CoreOS Cloud Init Installation`: ./cloudinit.html
