=====================================
Installation in Google Compute Engine
=====================================

This document describes how to install Kuryr-Kubernetes using
instances provided by Google Compute Engine.

The procedure is a variation of the general procedure described
in the `Cloud Installation Guide <cloud-install.html>`_.
Only the relevant steps will be explained, so be sure you
read the guide before attempting a gce-backed deployment.


Creating a network
------------------

Let's create a network for the GCE instances that we'll use as the underlay for
this deployment::

    $ gcloud compute networks create --range 10.142.0.0/24 demo

Once it is created, we should allow ssh and mosh access to the instances in the
deployment::

    $ gcloud compute firewall-rules create terminal --network demo --allow \
      tcp:22,udp:60000-61000

We should allow internal access too::

    $ gcloud compute firewall-rules create demo-allow-internal \
      --network demo --allow tcp:1-65535,udp:1-65535 \
      --source-ranges "10.142.0.0/24"

OST Controller
--------------

First, edit the :download:`cloud-config-ost-controller.yaml<./cloud-config-ost-controller.yaml>` as described in the `Cloud installation guide <cloud-install.html#ost-config>`_.

Let's provision an instance for the OST Controller

.. code-block:: bash

    $ gcloud compute --project "my_gce_project_name" instances create \
      "ost-controller" --zone "us-east1-b" \
      --custom-memory 16GiB --custom-cpu 4 \
      --network "demo" --can-ip-forward \
      --image-project "coreos-cloud" --image-family "coreos-stable" \
      --boot-disk-size "200" \
      --private-network-ip 10.142.0.2  \
      --maintenance-policy "MIGRATE"   \
      --metadata-from-file user-data=cloud-config-ost-controller.yaml


Then we enter the instance to set it up::

    $ gcloud compute ssh --zone us-east1-b "ost-controller"

Follow the same post-installation steps defined in the installation guide.


Kubernetes controller
---------------------

Edit the :download:`cloud-config-k8s-controller.yaml <./cloud-config-k8s-controller.yaml>` file
according to the `Cloud Installation Guide <cloud-install.html#k8s-config>`_.

Then create the controller instance::

    $ gcloud compute --project "my_gce_project_name" instances create \
      "k8s-controller" --zone "us-east1-b" \
      --custom-memory 8GiB --custom-cpu 4 \
      --network "demo" \
      --image-project "coreos-cloud" --image-family "coreos-stable" \
      --boot-disk-size "200" \
      --maintenance-policy "MIGRATE" \
      --private-network-ip 10.142.0.3 \
      --metadata-from-file user-data=cloud-config-k8s-controller.yaml
    Created
    [https://www.googleapis.com/compute/v1/projects/my_gce_project_name/zones/us-east1-b/instances/k8s-controller].
    NAME            ZONE        MACHINE_TYPE               PREEMPTIBLE
    INTERNAL_IP  EXTERNAL_IP      STATUS
    k8s-controller  us-east1-b  custom (2 vCPU, 8.00 GiB)
    10.142.0.3   104.196.134.170  RUNNING


Worker nodes
------------

Edit the :download:`cloud-config-k8s-worker.yaml <./cloud-config-k8s-worker.yaml>` file
according to the `Cloud Configuration Guide <cloud-install.html#worker-config>`_:


Using this cloud-config file you can create as many worker instances as you decide:

.. code-block:: bash

    $ gcloud compute --project "my_gce_project_name" instances create \
      "k8s-worker1" --zone "us-east1-b" \
      --custom-memory 12GiB --custom-cpu 6 \
      --network "demo" \
      --image-project "coreos-cloud" --image-family "coreos-stable" \
      --boot-disk-size "200" \
      --maintenance-policy "MIGRATE" \
      --private-network-ip 10.142.0.4 \
      --metadata-from-file user-data=cloud-config-k8s-worker.yaml
    Created
    [https://www.googleapis.com/compute/v1/projects/my_gce_project_name/zones/us-east1-b/instances/k8s-worker1].
    NAME            ZONE        MACHINE_TYPE               PREEMPTIBLE
    INTERNAL_IP  EXTERNAL_IP      STATUS
    k8s-worker1  us-east1-b  custom (2 vCPU, 8.00 GiB)
    10.142.0.4   104.196.134.170  RUNNING

Post-Installation
-----------------
Now you can go to the `Installation guide <installation.html#post-installation>`_ and continue with the installation procedure.
