#!/bin/bash

set -e
existing=$(ctx node properties use_external_resource)
if [ ${existing} -eq "true" ] ; then
    exit 0;
fi

PID=$(ctx instance runtime_properties pid)

kill -9 ${PID}

ctx logger info "Sucessfully stopped MongoDB (${PID})"