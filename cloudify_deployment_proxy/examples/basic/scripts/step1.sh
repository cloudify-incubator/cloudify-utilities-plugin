#!/bin/bash

set -e

ctx logger info "Step 1."
ctx instance runtime-properties environment_data "ABCD01234"
ctx instance runtime-properties application_data "0:1:2:3:4"
