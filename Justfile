# Copyright (c) Humanitarian OpenStreetMap Team
#
# This file is part of geojson-aoi-parser.
#
#     geojson-aoi-parser is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     geojson-aoi-parser is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with geojson-aoi-parser.  If not, see <https:#www.gnu.org/licenses/>.
#

set dotenv-load

# List available commands
[private]
default:
  just help

# List available commands
help:
  just --justfile {{justfile()}} --list

# Build container image
build:
  COMPOSE_BAKE=true docker compose build parser

# Run test suite
test:
  just build
  docker compose run --rm parser pytest
