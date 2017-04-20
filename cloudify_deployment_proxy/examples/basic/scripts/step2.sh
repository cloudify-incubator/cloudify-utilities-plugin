#!/bin/bash

set -e

ctx logger info "Step 2."
environment_data=$(ctx instance runtime-properties environment_data )
application_data=$(ctx instance runtime-properties application_data )
ctx instance runtime-properties combined_data (environment_data + application_data)
