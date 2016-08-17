================================
CoreOS Cloud Init Installation
================================

The coreos-cloudinit tool allows the automation of
service deployment using systemd. This document offers a
guide to install it from sources.

First, install go language according to the `official guide <https://golang.org/doc/install>`_
The rest of this guide assumes you have configured *$GOPATH* environment variable to point to
go language's root directory:

.. code-block:: bash

    $ cd $GOPATH

Download the coreos-cloudinit sources into the go working directory:

.. code-block:: bash

    $ git clone https://github.com/coreos/coreos-cloudinit.git src/github.com/coreos/coreos-cloudinit/

Now build the tool:

.. code-block:: bash

    $ go install github.com/coreos/coreos-cloudinit

Make the resulting binary accessible:

.. code-block:: bash

   $ ln -s $GOPATH/bin/coreos-cloudinit /opt/bin/coreos-cloudinit
