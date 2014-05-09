.. See file COPYING distributed with sjs for copyright and license.

This package contains an emulator for SGE, including scripts to emulate qsub, qdel, and qstat.

This package was written to support development of software that depends on SGE on a machine that doesn't (easily) support SGE, so the feature set and optimization is by design very limited.  I don't recommend using this as a production job scheduler.

Usage
=====

Set SJS_ROOT to the name of a directory that will contain information about the scheduler (its configuration, the queue, and the logs).  This directory should not exist, as it will be created when you initialize it with sjs_qconf:

::

    sjs_qconf init <number of slots>

The number of slots can be changed using ``sjs_qconf slots``:

::

    sjs_qconf slots <number of slots>

Jobs can be submitted and deleted using ``sjs_qsub`` and ``sjs_qdel`` as you would with ``qsub`` and ``qdel``, respectively, and a list of pending and running jobs can be displayed with ``sjs_qstat``.

For complete SGE emulation, link to the sjs_* scripts using the SGE names from somewhere in your path (e.g. ``/usr/local/bin/sjs_qsub`` -> ``/usr/bin/qsub``).

Dependencies
============

