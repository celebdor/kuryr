=====================================
Installation in Cloud Environments
=====================================

This document describes how to install Kuryr-Kubernetes using
instances provided by cloud providers, taking advantage of the
cloud-config files.

The procedure is a variation of the general procedure described
in the `Kuryr-Kubernetes Installation Guide <installation.html>`_.
Only the relevant differences will be explained, so be sure you
read the guide before attempting a cloud-backed deployment.

This guide documents the generic steps. Refer to the specific
guides for the `Google Compute Engine <gce-install.html>`_ and
`OpenStack <os-install.html>`_ backed deployments.

This guide assumes CoreOS instances for its native support for cloud-config
based instance initialization.

The principal difference resides in the impossibility to pass
initialization parameters other than those defined in the cloud-config
file. Therefore, the config files must be modified and passed as parameters
to the instance create command.

With respect of the differences between cloud platforms, the main difference
is regarding how you specify the cloud-config file when creating the instance.

For instance, in GCE, you specify it in the *metadata-from-file* directive,
as shown below:

.. code-block:: bash
   :emphasize-lines: 8

   $ gcloud compute --project "my_gce_project_name" instances create \
      "ost-controller" --zone "us-east1-b" \
      --network "demo" --can-ip-forward \
      --image-project "coreos-cloud" --image-family "coreos-stable" \
      --boot-disk-size "200" \
      --private-network-ip 10.142.0.2  \
      --maintenance-policy "MIGRATE"   \
      --metadata-from-file user-data=cloud-config-ost-controller.yaml

In an OpenStack-backed cloud infrastructure, the cloud-config fle is specified
un the *user-data* directive:

.. code-block:: bash
   :emphasize-lines: 4

   $ nova boot --flavor m2.large --image "CoreOS 1068.6.0"  \
      --nic net-name=demo,v4-fixed-ip=10.142.0.3 \
      --security-group demo --key-name demo-key k8s-controller \
      --user-data cloud-config-ost-controller.yaml



Creating a network
------------------

It is important to ensure your cloud deployment allows the communication
between the instances. How this is accomplished differs between providers.
Refer to specific guides for this step.


.. _ost-config:

OST Controller
--------------

First, edit the :download:`cloud-config-ost-controller.yaml<./cloud-config-ost-controlle.yaml>`
to set the LOCAL_IP parameter in the default */etc/conf.d/ost-controller-defaults* file
that will be created in the instance at provisioning time. You can leave the rest of defaults
as given:

.. code-block:: yaml

    write-files:
    ...
      - path: /etc/conf.d/ost-controller-defaults
        permissions: '0644'
        content: |
          LOCAL_IP=10.142.0.2
          DB_HOST=127.0.0.1
          DB_USERNAME=root
          DB_PASSWORD=root
          .
          .
          .
          C_SERVERS="127.0.0.1"
          C_FACTOR=1


Now, provision an instance for the OST Controller specifying the cloud-config
file as initializaton file. Once the instance is running, enter the instance
and follow the same post-installation steps defined in the `installation guide <installation.html#ost-post-install>`_.


Kubernetes controller
---------------------

Edit the :download:`cloud-config-k8s-controller.yaml <cloud-config-k8s-controller.yaml>` file
to add the required parameters to the default parameters file. The local ip and the ost-controller
ip are required:

.. code-block:: yaml
   :emphasize-lines: 6,7

    write-files:
    ...
      - path: /etc/conf.d/k8s-controller-defaults
        permissions: '0644'
        content: |
          LOCAL_IP=10.142.0.3
          OST_CONTROLLER=10.142.0.2
          OS_USERNAME=neutron
          OS_PASSWORD=neutron
          OS_TENANT_NAME=service

Then create the controller instance.


Worker nodes
------------

Edit the :download:`cloud-config-k8s-worker.yaml <./cloud-config-k8s-worker.yaml>` file to add the ost-controller and k8s-controller instances ip addressed:

.. code-block:: yaml
   :emphasize-lines: 6,7

    write-files:
    ...
      - path: /etc/conf.d/k8s-worker-defaults
        permissions: '0644'
        content: |
          OST_CONTROLLER=10.142.0.2
          K8S_CONTROLLER=10.142.0.3


The main difference between the worker nodes and the controller nodes, is that you may want to create
many worker instances. To facilitate this, the cloud-config file should not have any instance-specific
parameter. However, the installation process requires to know the worker's ip address. You can specify it via the `LOCAL_IP` parameter:

.. code-block:: yaml
   :emphasize-lines: 6

    write-files:
    ...
      - path: /etc/conf.d/k8s-worker-defaults
        permissions: '0644'
        content: |
          LOCAL_IP=10.142.0.4
          OST_CONTROLLER=10.142.0.2
          K8S_CONTROLLER=10.142.0.3

However, you will need to modify this parameter in the cloud-init file for each worker instance. Alternatively,
if you ommit this parameter, the */opt/bin/prepare-config.sh* script tries to discover this address
at installation time. It uses, if available, the name of the network interfaced used to connect to the worker's
network, which usually is the same for all instances:

.. code-block:: yaml
   :emphasize-lines: 6

    write-files:
    ...
      - path: /etc/conf.d/k8s-worker-defaults
        permissions: '0644'
        content: |
          INTERFACE=ens4v1
          OST_CONTROLLER=10.142.0.2
          K8S_CONTROLLER=10.142.0.3



Using this cloud-config file you can create as many worker instances as you decide.
On each worker, be sure you complete the post-installation procedure defined in the
`Installation guide <installation.html#worker-post-install>`_

Post-Installation
-----------------

Now you can go to the `Installation Guide <installation.html#post-installation>`_ and continue with the installation test procedure.
